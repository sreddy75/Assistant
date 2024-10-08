import streamlit as st
from utils.api_helpers import (
    get_confluence_pages,
    generate_development_artifacts,
    get_confluence_spaces,
    sync_confluence_pages,
    send_business_analysis_query
)
from .base_chat import BaseChat
from utils.helpers import send_event
from components.mermaid_chart import render_mermaid
import json
import time

class BusinessAnalysisChat(BaseChat):
    def __init__(self, system_chat_icon, user_chat_icon):
        super().__init__(system_chat_icon, user_chat_icon, "ba_messages", "ba_chat_input")
        self.org_id = None
        self.nodes = ["Analyze Business Documents", "Extract Key Requirements", "Generate User Stories", "Create Acceptance Criteria", "Generate Test Cases"]
        self.node_to_attr = {
            "Analyze Business Documents": "business_analysis",
            "Extract Key Requirements": "key_requirements",
            "Generate User Stories": "user_stories",
            "Create Acceptance Criteria": "acceptance_criteria",
            "Generate Test Cases": "test_cases"
        }
        self.attr_to_node = {v: k for k, v in self.node_to_attr.items()}

        if 'current_node_index' not in st.session_state:
            st.session_state.current_node_index = -1
        if 'analysis_results' not in st.session_state:
            st.session_state.analysis_results = {}
        if 'analysis_complete' not in st.session_state:
            st.session_state.analysis_complete = False
        if 'pages_loaded' not in st.session_state:
            st.session_state.pages_loaded = False
        if 'pages_synced' not in st.session_state:
            st.session_state.pages_synced = False
        if 'analysis_started' not in st.session_state:
            st.session_state.analysis_started = False

    def render_chat_interface(self, org_id):
        self.org_id = org_id

        # Custom CSS for expander titles and tabs
        st.markdown("""
            <style>
            div[data-testid="stExpander"] > div[role="button"] > div:first-child > div:first-child {
                font-weight: bold !important;
                font-size: 1.2em !important;
                color: red !important;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 2px;
            }
            .stTabs [data-baseweb="tab"] {
                height: 50px;
                white-space: pre-wrap;
                background-color: #F0F2F6;
                border-radius: 4px 4px 0 0;
                gap: 1px;
                padding-top: 10px;
                padding-bottom: 10px;
            }
            .stTabs [aria-selected="true"] {
                background-color: #FFFFFF;
            }
            </style>
        """, unsafe_allow_html=True)

        # Step 1: Load Confluence Spaces
        with st.expander("Step 1: Load Confluence Spaces", expanded=False):
            self.render_confluence_loader()

        # Step 2: Select Pages
        with st.expander("Step 2: Select Pages", expanded='confluence_pages' in st.session_state):
            self.render_page_selector()

        # Step 3: Perform Analysis
        with st.expander("Step 3: Perform Analysis", expanded='confluence_loaded' in st.session_state):
            self.render_analysis_interface()

        # Step 4: Chat with Analysis Results
        with st.expander("Step 4: Chat with Analysis Results", expanded=st.session_state.analysis_complete):
            super().render_chat_interface()

        # Final Results
        st.divider()
        if st.session_state.analysis_complete:
            self.display_final_results()

    def render_confluence_loader(self):
        spaces = get_confluence_spaces(self.org_id)
        
        if spaces is None or not spaces:
            st.warning("No Confluence spaces available. Please configure Confluence integration.")
        else:
            space_names = [space['name'] for space in spaces]
            selected_space_name = st.selectbox("Select Confluence Space", space_names, key="space_select_loader")
            selected_space = next(space for space in spaces if space['name'] == selected_space_name)

            if st.button("Load Pages"):
                pages = get_confluence_pages(self.org_id, selected_space['key'])
                if pages:
                    st.session_state.confluence_pages = pages
                    st.session_state.loaded_space_key = selected_space['key']
                    st.success(f"Pages loaded from '{selected_space_name}' successfully!")
                    if not st.session_state.pages_loaded:
                        send_event("confluence_pages_loaded", {"space_name": selected_space_name, "page_count": len(pages)})
                        st.session_state.pages_loaded = True
                else:
                    st.error("Failed to load pages. Please try again.")
                    send_event("confluence_pages_load_failed", {"space_name": selected_space_name})
                st.experimental_rerun()

    def render_page_selector(self):
        if 'confluence_pages' in st.session_state:
            selected_pages = st.multiselect(
                "Select pages to sync",
                options=[(page['id'], page['title']) for page in st.session_state.confluence_pages],
                format_func=lambda x: x[1]
            )

            if st.button("Sync Selected Pages"):
                with st.spinner("Syncing Confluence content..."):
                    result = sync_confluence_pages(self.org_id, st.session_state.loaded_space_key, [page[0] for page in selected_pages])
                if result.get("success", False):
                    st.success(f"Confluence content synced successfully! {result['result']['pages_synced']} pages synced.")
                    st.session_state.confluence_loaded = True
                    if not st.session_state.pages_synced:
                        send_event("confluence_pages_synced", {"page_count": result['result']['pages_synced']})
                        st.session_state.pages_synced = True
                else:
                    st.error(f"Failed to sync Confluence content. Error: {result.get('error', 'Unknown error')}")
                    send_event("confluence_sync_failed", {"error": result.get('error', 'Unknown error')})
                st.experimental_rerun()
        else:
            st.info("Please load Confluence pages in Step 1 first.")

    def render_analysis_interface(self):
        self.chart_placeholder = st.empty()
        self.display_mermaid_chart()

        col1, col2 = st.columns([3, 1])
        self.progress_placeholder = col1.empty()
        self.status_placeholder = col2.empty()

        if st.button("Perform Business Analysis"):
            st.session_state.analysis_complete = False
            st.session_state.analysis_results = {}
            st.session_state.current_node_index = -1
            st.session_state.analysis_started = True
            st.experimental_rerun()

        if st.session_state.analysis_started and not st.session_state.analysis_complete:
            self.perform_business_analysis()

    def perform_business_analysis(self):
        try:
            send_event("business_analysis_started", {})
            start_time = time.time()
            response_iterator = generate_development_artifacts(self.org_id)
            
            for response in response_iterator:
                response_obj = json.loads(response)
                
                if "graph_state" in response_obj:
                    current_attr = list(response_obj["graph_state"].keys())[0]
                    current_node = self.attr_to_node.get(current_attr)
                    if current_node:
                        st.session_state.current_node_index = self.nodes.index(current_node)
                    
                        # Update Mermaid chart
                        self.display_mermaid_chart()
                    
                        # Update analysis results
                        st.session_state.analysis_results.update(response_obj["graph_state"])
                    
                        # Update progress and status
                        completed_steps = st.session_state.current_node_index + 1
                        progress = completed_steps / len(self.nodes)
                        self.progress_placeholder.progress(progress)
                        self.status_placeholder.text(f"step {completed_steps}/{len(self.nodes)}")
                        send_event("business_analysis_step_executed", {"step": current_node, "progress": progress})
                    
                        # Give Streamlit a moment to update the UI
                        time.sleep(0.5)
                
                if response_obj.get("is_final", False):
                    st.session_state.analysis_results["final_results"] = response_obj["graph_state"]
                    st.session_state.analysis_complete = True
            
            # Hide the Mermaid chart, progress, and status after analysis completion
            self.chart_placeholder.empty()
            self.progress_placeholder.empty()
            self.status_placeholder.empty()

            duration = time.time() - start_time
            send_event("business_analysis_completed", {"duration": duration})

        except Exception as e:
            st.error(f"An error occurred while performing business analysis: {str(e)}")
            send_event("business_analysis_error", {"error": str(e)})
        finally:
            st.session_state.analysis_started = False
            st.experimental_rerun()

    def display_mermaid_chart(self):
        mermaid_code = self.update_mermaid_chart()
        with self.chart_placeholder:
            render_mermaid(mermaid_code, height=50)

    def update_mermaid_chart(self):
        current_index = st.session_state.current_node_index
        
        mermaid_code = """
        %%{init: {'theme': 'base', 'themeVariables': { 'lineColor': '#ffffff' }}}%%
        flowchart LR
            A[Analyzing Docs]
            B[Extracting Reqs]
            C[Generating Stories]
            D[Writing AC's]
            E[Documenting Tests]
            A --> B --> C --> D --> E
        """

        for i, node in enumerate(self.nodes):
            node_id = chr(65 + i)  # A, B, C, D, E
            if current_index == -1 or i > current_index:
                # Pending nodes (including initial state)
                mermaid_code += f"\n    style {node_id} fill:#FFFFFF,stroke:#333,stroke-width:2px"
            elif i < current_index:
                # Completed nodes
                mermaid_code += f"\n    style {node_id} fill:#90EE90,stroke:#333,stroke-width:2px"
            elif i == current_index:
                # Current node
                mermaid_code += f"\n    style {node_id} fill:#e5ed05,stroke:#d95e00,stroke-width:2px"

        return mermaid_code

    def display_final_results(self):
        final_results = st.session_state.analysis_results.get("final_results", {})
        
        st.markdown("## Final Analysis Results")
        
        if final_results:
            tabs = st.tabs([key.replace("_", " ").title() for key in final_results.keys()])
            for tab, (key, value) in zip(tabs, final_results.items()):
                with tab:
                    st.write(value)
        else:
            st.info("No final results available yet.")

    def send_message(self, message):
        send_event("business_analysis_message_sent", {"message_length": len(message)})
        return send_business_analysis_query(message, st.session_state.analysis_results, self.org_id)

    def get_input_placeholder(self):
        return "Ask about the analysis results"