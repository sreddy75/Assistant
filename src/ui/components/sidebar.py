# sidebar.py

import streamlit as st
from kr8.tools.pandas import PandasTools
from kr8.tools.code_tools import CodeTools
from ui.utils.helper import restart_assistant
from utils.npm_utils import run_npm_command
from config.client_config import ENABLED_ASSISTANTS

def initialize_session_state(user_role):
    role_assistants = {
        "Dev": ["Web Search", "Code Assistant"],
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
    st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)
    
    role_assistants = {
        "Dev": ["Web Search", "Code Assistant"],
        "QA": ["Web Search", "Enhanced Quality Analyst", "Business Analyst"],
        "Product": ["Web Search", "Product Owner", "Business Analyst", "Enhanced Data Analyst"],
        "Delivery": ["Web Search", "Business Analyst", "Enhanced Data Analyst"],
        "Manager": ["Web Search", "Enhanced Financial Analyst", "Business Analyst", "Enhanced Data Analyst"]
    }
    
    available_assistants = role_assistants.get(user_role, [])
    
    with st.sidebar.expander("Available Assistants", expanded=False):
        for assistant in ENABLED_ASSISTANTS:
            if assistant in available_assistants:
                key = f"{assistant.lower().replace(' ', '_')}_enabled"
                enabled = st.checkbox(assistant, value=st.session_state.get(key, True))
                if st.session_state.get(key) != enabled:
                    st.session_state[key] = enabled
                    restart_assistant()
    
    st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)
    st.sidebar.subheader("Project Upload")
    
    project_type = st.sidebar.selectbox("Select Project Type", ["React", "Java"])
    project_name = st.sidebar.text_input(f"Enter Project Name")
    
    file_types = ["js", "jsx", "ts", "tsx", "css", "json", "html", "md", "yml", "yaml", "txt"]
    if project_type == "Java":
        file_types.extend(["java", "xml", "properties", "gradle"])
    
    project_files = st.sidebar.file_uploader(
        f"Upload {project_type} Project Files", 
        type=file_types,
        key="project_file_uploader",
        accept_multiple_files=True
    )
    
    if project_files:
        if 'project_files_processed' not in st.session_state:
            st.session_state.project_files_processed = False
        
        if not st.session_state.project_files_processed:
            st.sidebar.info(f"{project_type} files uploaded. Click 'Process {project_type} Project' to analyze them.")
        
        if st.sidebar.button(f"Process {project_type} Project"):
            process_project(project_type, project_name, project_files)
    else:
        st.session_state.project_files_processed = False
    
    if st.session_state.get('current_project') and st.session_state.get('project_files_processed', False):
        st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)
        st.sidebar.subheader(f"{project_type} Project Tools")
        
        if st.sidebar.button("Analyze Project Structure"):
            analyze_project_structure(project_name, project_type.lower())
        
        if st.sidebar.button("Show Dependency Graph"):
            show_dependency_graph(project_name, project_type.lower())
        
        if project_type == "Java":
            if st.sidebar.button("Show Java Project Analysis"):
                show_java_project_analysis(project_name)
    
    st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)
    
    render_model_selection()

def process_project(project_type, project_name, project_files):
    progress_bar = st.empty()
    status_text = st.empty()
    
    with st.spinner(f"Processing {project_type} project files..."):
        try:
            directory_content = {}
            total_files = len(project_files)
            
            for i, file in enumerate(project_files):
                file_content = file.read().decode('utf-8', errors='ignore')
                directory_content[file.name] = file_content
                
                progress = (i + 1) / total_files
                progress_bar.progress(progress)
                status_text.text(f"Processing file {i+1} of {total_files}: {file.name}")

            llm_os = st.session_state.get("llm_os")
            if llm_os and llm_os.knowledge_base:
                # Set the project context for the LLM
                llm_os.set_project_context(project_name, project_type.lower())
                
                code_tools = CodeTools(knowledge_base=llm_os.knowledge_base)
                result = code_tools.load_project(project_name, project_type.lower(), directory_content)
                st.success(result)
                st.session_state['current_project'] = project_name
                st.session_state['current_project_type'] = project_type.lower()
                st.session_state.project_files_processed = True
            else:
                st.error("LLM OS or knowledge base not initialized. Please try restarting the application.")
        except Exception as e:
            st.error(f"Error processing {project_type} project files: {str(e)}")
        finally:
            progress_bar.empty()
            status_text.empty()

def analyze_project_structure(project_name, project_type):
    llm_os = st.session_state.get("llm_os")
    if llm_os:
        code_tools = CodeTools(knowledge_base=llm_os.knowledge_base)
        result = code_tools.analyze_project_structure(project_name, project_type)
        st.json(result)
    else:
        st.sidebar.error("LLM OS not initialized. Please try restarting the application.")

def show_dependency_graph(project_name, project_type):
    llm_os = st.session_state.get("llm_os")
    if llm_os:
        code_tools = CodeTools(knowledge_base=llm_os.knowledge_base)
        dependency_graph = code_tools.get_dependency_graph(project_name, project_type)
        if dependency_graph:
            st.json(dependency_graph)
        else:
            st.warning(f"No dependency graph found for {project_type} project '{project_name}'")
    else:
        st.sidebar.error("LLM OS not initialized. Please try restarting the application.")

def show_java_project_analysis(project_name):
    llm_os = st.session_state.get("llm_os")
    if llm_os:
        code_tools = CodeTools(knowledge_base=llm_os.knowledge_base)
        analysis = code_tools.analyze_project_structure(project_name, "java")
        if analysis:
            st.json(analysis)
        else:
            st.warning(f"No project analysis found for Java project '{project_name}'")
    else:
        st.sidebar.error("LLM OS not initialized. Please try restarting the application.")

def render_model_selection():
    with st.sidebar.expander("Select model:", expanded=False):
        model_type = st.sidebar.radio("Select Model Type", ["Closed", "Open Source"])

        if model_type == "Closed":
            llm_options = ["gpt-4o", "claude-3.5"]
            llm_id = st.sidebar.selectbox("Select Closed Source Model", options=llm_options)
        else: 
            llm_options = ["llama3", "tinyllama"]
            llm_id = st.sidebar.selectbox("Select Open Source Model", options=llm_options)
        
        if "llm_id" not in st.session_state:
            st.session_state["llm_id"] = llm_id
        elif st.session_state["llm_id"] != llm_id:
            st.session_state["llm_id"] = llm_id
            restart_assistant()