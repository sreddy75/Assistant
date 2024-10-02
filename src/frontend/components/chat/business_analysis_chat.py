import streamlit as st
from components.mermaid_chart import render_mermaid
from utils.api_helpers import (
    get_confluence_pages,
    generate_development_artifacts,
    get_confluence_spaces,
    sync_confluence_pages,
    send_business_analysis_query
)
import time
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusinessAnalysisChat:
    def __init__(self, system_chat_icon, user_chat_icon):
        self.system_chat_icon = system_chat_icon
        self.user_chat_icon = user_chat_icon
        self.org_id = None
        self.message_key = "ba_chat_messages"
        self.chat_input_key = "ba_chat_input"
        

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
        if self.message_key not in st.session_state:
            st.session_state[self.message_key] = []
        if "ba_processing" not in st.session_state:
            st.session_state.ba_processing = False
        if self.chat_input_key not in st.session_state:
            st.session_state[self.chat_input_key] = ""
        
        # Initialize placeholders
        self.chart_placeholder = st.empty()
        self.progress_placeholder = st.empty()
        self.status_placeholder = st.empty()        
        self.final_results_placeholder = st.empty()
        self.response_container = st.empty()

    def render_chat_interface(self, org_id):
        self.org_id = org_id                        

        # Custom CSS for expander titles
        st.markdown("""
            <style>
            .streamlit-expanderHeader {
                font-weight: bold;
                font-size: 25px;
                color: #079107;
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
            # Mermaid chart
            self.chart_placeholder = st.empty()
            self.display_mermaid_chart() 

            # Progress and status
            col1, col2 = st.columns([3, 1])
            self.progress_placeholder = col1.empty()
            self.status_placeholder = col2.empty()            
            
            # Button to start analysis
            if st.button("Perform Business Analysis"):
                st.session_state.analysis_complete = False
                st.session_state.analysis_results = {}
                st.session_state.current_node_index = -1
                self.perform_business_analysis()

        # Step 4: Chat with Analysis Results
        with st.expander("Step 4: Chat with Analysis Results", expanded=st.session_state.analysis_complete):
            self.render_chat_with_results()

        # Final Results
        st.markdown("---")  # Add a divider        
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
                else:
                    st.error("Failed to load pages. Please try again.")

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
                else:
                    st.error(f"Failed to sync Confluence content. Error: {result.get('error', 'Unknown error')}")
        else:
            st.info("Please load Confluence pages in Step 1 first.")

    def perform_business_analysis(self):
        try:
            response_iterator = generate_development_artifacts(self.org_id)
            
            for response in response_iterator:
                response_obj = json.loads(response)
                logger.info(f"Received response: {response_obj}")
                
                if "graph_state" in response_obj:
                    current_attr = list(response_obj["graph_state"].keys())[0]
                    current_node = self.attr_to_node.get(current_attr)
                    if current_node:
                        st.session_state.current_node_index = self.nodes.index(current_node)
                    
                        logger.info(f"Processing node: {current_node}")
                    
                        # Update Mermaid chart
                        self.display_mermaid_chart()
                    
                        # Update analysis results
                        st.session_state.analysis_results.update(response_obj["graph_state"])
                    
                        # Update progress and status
                        completed_steps = st.session_state.current_node_index + 1
                        progress = completed_steps / len(self.nodes)
                        self.progress_placeholder.progress(progress)
                        self.status_placeholder.text(f"step {completed_steps}/{len(self.nodes)}")
                    
                        # Give Streamlit a moment to update the UI
                        time.sleep(0.5)
                
                if response_obj.get("is_final", False):
                    logger.info("Received final results")
                    st.session_state.analysis_results["final_results"] = response_obj["graph_state"]
                    st.session_state.analysis_complete = True
            
            logger.info("Business analysis completed")
            # Hide the Mermaid chart, progress, and status after analysis completion
            self.chart_placeholder.empty()
            self.progress_placeholder.empty()
            self.status_placeholder.empty()
        except Exception as e:
            st.error(f"An error occurred while performing business analysis: {str(e)}")
            logger.exception("Error in perform_business_analysis")

    def render_chat_with_results(self):
        st.subheader("Chat with Analysis Results")
        
        chat_container = st.container()
        input_container = st.container()

        with chat_container:
            self.render_messages()
            if st.session_state.ba_processing:
                self.show_thinking_animation()

        with input_container:
            if not st.session_state.ba_processing:
                col1, col2 = st.columns([20, 1])
                with col1:
                    user_input = st.text_input(
                        "Ask about the analysis results",
                        key=self.chat_input_key,
                        value=""
                    )
                with col2:
                    st.markdown(
                        """
                        <style>
                        .stButton > button {
                            position: relative;
                            top: 14px;
                            left: 5px;
                            height: 38px;
                            padding: 0 10px;                            
                            color: white;
                            border: none;
                            border-radius: 8px;
                            cursor: pointer;
                            transition: background-color 0.3s;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                    )
                    if st.button("↑", key="send_ba_chat"):
                        self.handle_input(user_input)
                        st.session_state[self.chat_input_key] = ""

                st.button("Clear Conversation", key="clear_ba_chat", on_click=self.clear_chat_history)
            else:
                st.empty()
                st.empty()

        if st.session_state.ba_processing:
            self.process_message()

    def show_thinking_animation(self, color="#f71905", size="20px"):
        css = f"""
        <style>
        @keyframes ellipsis {{
            0% {{ content: '..'; }}
            33% {{ content: '....'; }}
            66% {{ content: '.....'; }}
        }}
        .thinking::after {{
            content: '.';
            animation: ellipsis 1s infinite;
            color: {color};
            font-size: {size};
            line-height: 0;
            vertical-align: middle;
        }}
        .thinking-text {{
            color: {color};
            font-size: {size};
            display: inline-block;
            vertical-align: middle;
            margin-right: 5px;
        }}
        </style>
        """
        html = f"{css}<div><span class='thinking-text'>Thinking</span><span class='thinking'></span></div>"
        st.markdown(html, unsafe_allow_html=True)

    def handle_input(self, user_input):
        if user_input and not st.session_state.ba_processing:
            st.session_state.ba_processing = True
            st.session_state[self.message_key].append({"role": "user", "content": user_input})
            st.experimental_rerun()

    def process_message(self):
        try:
            user_input = st.session_state[self.message_key][-1]["content"]
            response = send_business_analysis_query(user_input, st.session_state.analysis_results, self.org_id)

            full_response = ""
            for chunk in response:
                if chunk:
                    full_response += chunk
                    self.response_container.markdown(full_response)
                    time.sleep(0.02)

            st.session_state[self.message_key].append({"role": "assistant", "content": full_response})
        except Exception as e:
            st.error(f"An error occurred while processing your request: {str(e)}")
        finally:
            st.session_state.ba_processing = False
            st.experimental_rerun()

    def render_messages(self):
        for message in st.session_state[self.message_key]:
            with st.chat_message(message["role"], avatar=self.system_chat_icon if message["role"] == "assistant" else self.user_chat_icon):
                st.markdown(message["content"])

    def clear_chat_history(self):
        st.session_state[self.message_key] = []
        st.session_state.ba_processing = False
        st.session_state[self.chat_input_key] = ""
        if hasattr(self, 'response_container'):
            self.response_container.empty()
        st.experimental_rerun()

    def update_mermaid_chart(self):
        current_index = st.session_state.current_node_index
        
        mermaid_code = """
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

    def display_mermaid_chart(self):
        mermaid_code = self.update_mermaid_chart()
        with self.chart_placeholder:
            render_mermaid(mermaid_code, height=50)

    def display_final_results(self):
        final_results = st.session_state.analysis_results.get("final_results", {})
        
        with self.final_results_placeholder.container():
            st.markdown("## Final Analysis Results")
            
            for key, value in final_results.items():
                with st.expander(key.replace("_", " ").title(), expanded=False):
                    st.write(value)

        logger.info("Final results displayed")