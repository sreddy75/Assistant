from asyncio.log import logger
import streamlit as st
from kr8.tools.pandas import PandasTools
from kr8.tools.code_tools import CodeTools
from ui.utils.helper import restart_assistant
from utils.npm_utils import run_npm_command
from config.client_config import ENABLED_ASSISTANTS

def initialize_session_state(user_role):
    
    role_assistants = {
        "QA": ["Web Search", "Enhanced Quality Analyst", "Business Analyst"],
        "Product": ["Web Search", "Product Owner", "Business Analyst", "Enhanced Data Analyst"],
        "Delivery": ["Web Search", "Business Analyst", "Enhanced Data Analyst"],
        "Manager": ["Web Search", "Enhanced Financial Analyst", "Business Analyst", "Enhanced Data Analyst"]
    }
    
    available_assistants = role_assistants.get(user_role, [])
    
    for assistant in ENABLED_ASSISTANTS:
        key = f"{assistant.lower().replace(' ', '_')}_enabled"
        if key not in st.session_state:
            st.session_state[key] = assistant in available_assistants
    
    if 'pandas_tools' not in st.session_state:
        st.session_state.pandas_tools = PandasTools()

def render_sidebar():
    user_role = st.session_state.get('role')
    initialize_session_state(user_role)    
    st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)  # Add divider            
    
    role_assistants = {
        "QA": ["Web Search", "Enhanced Quality Analyst", "Business Analyst"],
        "Product": ["Web Search", "Product Owner", "Business Analyst", "Enhanced Data Analyst"],
        "Delivery": ["Web Search", "Business Analyst", "Enhanced Data Analyst"],
        "Manager": ["Web Search", "Enhanced Financial Analyst", "Business Analyst", "Enhanced Data Analyst"]
    }
    
    available_assistants = role_assistants.get(user_role, [])
    
    # In the sidebar, only show enabled assistants for the user's role
    with st.sidebar.expander("Available Assistants", expanded=False):
        for assistant in ENABLED_ASSISTANTS:
            if assistant in available_assistants:
                key = f"{assistant.lower().replace(' ', '_')}_enabled"
                enabled = st.checkbox(assistant, value=st.session_state.get(key, True))
                if st.session_state.get(key) != enabled:
                    st.session_state[key] = enabled
                    restart_assistant()                    
    
    # Only show React Project Upload if React Assistant is enabled and available for the user's role
    if st.session_state.get("react_assistant_enabled", False) and "ReactAssistant" in available_assistants:
        st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)
        st.sidebar.subheader("React Project Upload")
            
        # Check if npm is installed
        if run_npm_command("--version") is None:
            st.sidebar.warning("npm is not installed or not in PATH. Some features may not work correctly.")
            
        # File uploader
        react_files = st.sidebar.file_uploader(
            "Upload React Project Files", 
            type=["js", "jsx", "ts", "tsx", "css", "json", "html", "md", "yml", "yaml", "txt"],
            key="react_file_uploader",
            accept_multiple_files=True
        )
        
        # Project name input
        project_name = st.sidebar.text_input("Enter React Project Name", "my_react_project")
        
        # Process files when they are uploaded
        if react_files:
            if 'react_files_processed' not in st.session_state:
                st.session_state.react_files_processed = False
            
            if not st.session_state.react_files_processed:
                st.sidebar.info("React files uploaded. Click 'Process React Project' to analyze them.")
            
            if st.sidebar.button("Process React Project"):
                # Create placeholders in the main area for progress bar and status
                progress_bar = st.empty()
                status_text = st.empty()
                
                with st.spinner("Processing React project files..."):
                    try:
                        directory_content = {}
                        total_files = len(react_files)
                        
                        for i, file in enumerate(react_files):
                            file_content = file.read().decode('utf-8', errors='ignore')
                            directory_content[file.name] = file_content
                            
                            # Update progress
                            progress = (i + 1) / total_files
                            progress_bar.progress(progress)
                            status_text.text(f"Processing file {i+1} of {total_files}: {file.name}")

                        # Use the LLM OS from the session state
                        llm_os = st.session_state.get("llm_os")
                        if llm_os and llm_os.knowledge_base:
                            code_tools = CodeTools(knowledge_base=llm_os.knowledge_base)
                            result = code_tools.load_react_project(project_name, directory_content)
                            st.success(result)
                            st.session_state['current_project'] = project_name
                            st.session_state.react_files_processed = True
                        else:
                            st.error("LLM OS or knowledge base not initialized. Please try restarting the application.")
                    except Exception as e:
                        st.error(f"Error processing React project files: {str(e)}")
                        logger.error(f"Error processing React project files: {str(e)}")
                    finally:
                        # Clear the progress bar and status text
                        progress_bar.empty()
                        status_text.empty()
        else:
            st.session_state.react_files_processed = False
        
        # React Assistant Tools
        if st.session_state.get('current_project') and st.session_state.get('react_files_processed', False):
            st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)
            st.sidebar.subheader("React Assistant Tools")
            project_name = st.session_state['current_project']
            
            if st.sidebar.button("Analyze Project Structure"):
                llm_os = st.session_state.get("llm_os")
                if llm_os:
                    result = llm_os.run(f"Analyze the structure of the React project named {project_name}")
                    st.write(result)
                else:
                    st.sidebar.error("LLM OS not initialized. Please try restarting the application.")
                            
    st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)  # Add divider            
                    
    with st.sidebar.expander("Select model:", expanded=False):
        # Model Type Selection
        model_type = st.sidebar.radio("Select Model Type", ["Closed", "Open Source"])

        # Model Selection based on type
        if model_type == "Closed": # Closed Source
            llm_options = ["gpt-4o", "claude-3.5"]
            llm_id = st.sidebar.selectbox("Select Closed Source Model", options=llm_options)
        else: 
            llm_options = ["llama3", "tinyllama"]
            llm_id = st.sidebar.selectbox("Select Open Source Model", options=llm_options)
        
        # Update session state and restart assistant if necessary
        if "llm_id" not in st.session_state:
            st.session_state["llm_id"] = llm_id
        elif st.session_state["llm_id"] != llm_id:
            st.session_state["llm_id"] = llm_id
            restart_assistant()