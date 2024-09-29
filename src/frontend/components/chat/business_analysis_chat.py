import streamlit as st
from utils.api_helpers import (
    get_confluence_pages,
    generate_development_artifacts,
    get_confluence_spaces,
    sync_confluence_pages
)
import time
import graphviz
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusinessAnalysisChat:
    def __init__(self, system_chat_icon, user_chat_icon):
        self.system_chat_icon = system_chat_icon
        self.user_chat_icon = user_chat_icon
        self.org_id = None

        self.nodes = ["AnalyzeBusinessDocuments", "ExtractKeyRequirements", "GenerateUserStories", "CreateAcceptanceCriteria", "GenerateTestCases"]
        self.node_to_attr = {
            "AnalyzeBusinessDocuments": "business_analysis",
            "ExtractKeyRequirements": "key_requirements",
            "GenerateUserStories": "user_stories",
            "CreateAcceptanceCriteria": "acceptance_criteria",
            "GenerateTestCases": "test_cases"
        }
        self.attr_to_node = {v: k for k, v in self.node_to_attr.items()}

        if 'graph' not in st.session_state:
            st.session_state.graph = self.initialize_graph()
        if 'analysis_results' not in st.session_state:
            st.session_state.analysis_results = {}
        if 'analysis_complete' not in st.session_state:
            st.session_state.analysis_complete = False
        
        # Initialize placeholders
        self.graph_placeholder = None
        self.progress_placeholder = None
        self.status_placeholder = None
        self.step_placeholders = {}
        self.final_results_placeholder = None

        self.nodes = ["AnalyzeBusinessDocuments", "ExtractKeyRequirements", "GenerateUserStories", "CreateAcceptanceCriteria", "GenerateTestCases"]
        self.node_to_attr = {
            "AnalyzeBusinessDocuments": "business_analysis",
            "ExtractKeyRequirements": "key_requirements",
            "GenerateUserStories": "user_stories",
            "CreateAcceptanceCriteria": "acceptance_criteria",
            "GenerateTestCases": "test_cases"
        }
        self.attr_to_node = {v: k for k, v in self.node_to_attr.items()}

    def render_chat_interface(self, org_id):
        self.org_id = org_id        

        # Sidebar for Confluence Loader
        with st.sidebar:
            st.header("Confluence Data Loader")
            self.render_confluence_loader()        

        # Main area split into two columns
        col1, col2 = st.columns([4, 1])

        with col1:            
            st.header("Business Analysis Results")            
        
            # Create placeholders for each component
            self.progress_placeholder = st.empty()
            self.status_placeholder = st.empty()            
            
            self.step_placeholders = {
                "AnalyzeBusinessDocuments": st.empty(),
                "ExtractKeyRequirements": st.empty(),
                "GenerateUserStories": st.empty(),
                "CreateAcceptanceCriteria": st.empty(),
                "GenerateTestCases": st.empty()
            }
            self.final_results_placeholder = st.empty()
            
            if st.button("Perform Business Analysis"):
                st.session_state.analysis_complete = False
                st.session_state.analysis_results = {}
                st.session_state.graph = self.initialize_graph()
                self.perform_business_analysis()                                                    

        with col2:
            st.header("Analysis Progress")
            self.graph_placeholder = st.empty()
            self.display_graph()

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
                    st.success(f"Pages loaded from '{selected_space_name}' successfully!")
                else:
                    st.error("Failed to load pages. Please try again.")

            if 'confluence_pages' in st.session_state:
                selected_pages = st.multiselect(
                    "Select pages to sync",
                    options=[(page['id'], page['title']) for page in st.session_state.confluence_pages],
                    format_func=lambda x: x[1]
                )

                if st.button("Sync Selected Pages"):
                    with st.spinner("Syncing Confluence content..."):
                        result = sync_confluence_pages(self.org_id, selected_space['key'], [page[0] for page in selected_pages])
                    if result.get("success", False):
                        st.success(f"Confluence content synced successfully! {result['result']['pages_synced']} pages synced.")
                        st.session_state.confluence_loaded = True
                        st.session_state.loaded_space_key = selected_space['key']
                    else:
                        st.error(f"Failed to sync Confluence content. Error: {result.get('error', 'Unknown error')}")

    def perform_business_analysis(self):
        try:
            response_iterator = generate_development_artifacts(self.org_id)
            for response in response_iterator:
                self.process_response(response)
            st.session_state.analysis_complete = True
        except Exception as e:
            st.error(f"An error occurred while performing business analysis: {str(e)}")
            logger.exception("Error in perform_business_analysis")

    def process_response(self, response):
        try:
            response_obj = json.loads(response)
            logger.info(f"Received response: {response_obj}")
            if "graph_state" in response_obj:
                self.update_graph(response_obj["graph_state"])
                st.session_state.analysis_results.update(response_obj["graph_state"])
                current_attr = list(response_obj["graph_state"].keys())[0]
                current_node = self.attr_to_node.get(current_attr, current_attr)
                
                # Update progress and status
                completed_steps = self.nodes.index(current_node) + 1 if current_node in self.nodes else 0
                progress = completed_steps / len(self.nodes)
                self.progress_placeholder.progress(progress)
                self.status_placeholder.text(f"Completed: {completed_steps}/{len(self.nodes)} steps")

                # Display interim results
                if current_node in self.step_placeholders:
                    with self.step_placeholders[current_node].expander(f"Interim Result: {current_node}", expanded=True):
                        st.write(response_obj["graph_state"][current_attr])
                else:
                    logger.warning(f"No placeholder found for node: {current_node}")
            
            if response_obj.get("is_final", False):
                st.session_state.analysis_results["final_results"] = response_obj["graph_state"]
                self.display_final_results()
        except json.JSONDecodeError:
            logger.warning(f"Received non-JSON response: {response}")
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}", exc_info=True)

    def initialize_graph(self):
        graph = graphviz.Digraph()
        graph.attr(rankdir='TB')
        for node in self.nodes:
            graph.node(node, node, shape='box')
        for i in range(len(self.nodes) - 1):
            graph.edge(self.nodes[i], self.nodes[i+1])
        return graph

    def update_graph(self, graph_state):
        completed_attr = list(graph_state.keys())[0]
        completed_node = self.attr_to_node.get(completed_attr)
        
        if completed_node is None:
            logger.warning(f"Unknown attribute in graph_state: {completed_attr}")
            return

        completed_index = self.nodes.index(completed_node) if completed_node in self.nodes else -1

        for i, node in enumerate(self.nodes):
            if i <= completed_index:
                st.session_state.graph.node(node, node, style='filled', color='lightgreen', shape='box')
                if i > 0:
                    st.session_state.graph.edge(self.nodes[i-1], node, color='green')
            else:
                st.session_state.graph.node(node, node, shape='box')
        self.display_graph()

    def display_graph(self):
        if self.graph_placeholder is not None:
            try:
                self.graph_placeholder.graphviz_chart(st.session_state.graph)
            except Exception as e:
                logger.error(f"Error displaying graph: {str(e)}", exc_info=True)
                self.graph_placeholder.error("Unable to display graph. Please check the console for more information.")

    def display_final_results(self):
        final_results = st.session_state.analysis_results.get("final_results", {})
        
        with self.final_results_placeholder.container():
            st.markdown("## Final Business Analysis Results")
            
            for key, value in final_results.items():
                with st.expander(key.replace("_", " ").title(), expanded=True):
                    st.write(value)

        logger.info("Final results displayed")

def main():
    st.set_page_config(page_title="Business Analysis Chat", layout="wide")
    
    # Assuming you have the org_id stored in session state or retrieved from elsewhere
    org_id = st.session_state.get('org_id')
    
    chat = BusinessAnalysisChat(system_chat_icon="🤖", user_chat_icon="👤")
    chat.render_chat_interface(org_id)

if __name__ == "__main__":
    main()