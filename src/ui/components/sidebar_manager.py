# sidebar.py

import json
import streamlit as st
from src.backend.kr8.tools.pandas import PandasTools
from src.backend.kr8.tools.code_tools import CodeTools
from ui.utils.helper import restart_assistant
from ui.components.knowledge_base_manager import manage_knowledge_base
from backend.core.client_config import ENABLED_ASSISTANTS
import matplotlib.pyplot as plt
from backend.db.session import get_db
from backend.utils.org_utils import load_org_config

def initialize_session_state(user_role):
    # Fetch the organization ID from the session state
    org_id = st.session_state.get('org_id')
    if not org_id:
        st.error("Organization ID not found in session state.")
        return

    # Load the organization-specific config
    db = next(get_db())
    try:
        org_config = load_org_config(org_id)
    except Exception as e:
        st.error(f"Failed to load organization config: {str(e)}")
        return
    finally:
        db.close()

    # Get the role-specific assistants from the org config
    role_assistants = org_config.get('assistants', {}).get(user_role, [])

    # Initialize assistant states based on the config
    for assistant in ENABLED_ASSISTANTS:
        key = f"{assistant.lower().replace(' ', '_')}_enabled"
        if key not in st.session_state:
            st.session_state[key] = assistant in role_assistants

    # Initialize PandasTools if not already done
    if 'pandas_tools' not in st.session_state:
        st.session_state.pandas_tools = PandasTools()

    # Store the full org config in the session state for later use
    st.session_state['org_config'] = org_config

def render_sidebar():
    user_role = st.session_state.get('role')
    if not user_role:
        st.sidebar.error("User role not found. Please log in again.")
        return    
    
    initialize_session_state(user_role)
    st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)
    
    org_config = st.session_state.get('org_config')
    if not org_config:
        st.sidebar.error("Organization configuration not loaded. Please refresh the page.")
        return

    available_assistants = org_config.get('assistants', {}).get(user_role, [])
    
    with st.sidebar.expander("Available Assistants", expanded=False):
        for assistant in ENABLED_ASSISTANTS:
            if assistant in available_assistants:
                key = f"{assistant.lower().replace(' ', '_')}_enabled"
                enabled = st.checkbox(assistant, value=st.session_state.get(key, True))
                if st.session_state.get(key) != enabled:
                    st.session_state[key] = enabled
                    restart_assistant()
    
    # Check if Code Assistant is enabled
    if "Code Assistant" in available_assistants:        
        st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)
        st.sidebar.subheader("Project Management")
    
        project_type = st.sidebar.selectbox("Select Project Type", ["React", "Java"])
        project_name = st.sidebar.text_input(f"Enter Project Name")
        
        file_types = ["js", "jsx", "ts", "tsx", "css", "json", "html", "md", "yml", "yaml", "txt"]
        if project_type == "Java":
            file_types.extend(["java", "xml", "properties", "gradle"])
        
        project_files = st.sidebar.file_uploader(
            f"Upload {project_type} Project Files or Directory", 
            type=file_types,
            key="project_file_uploader",
            accept_multiple_files=True
        )
        
        if project_files:
            if 'project_files_processed' not in st.session_state:
                st.session_state.project_files_processed = False
            
            if not st.session_state.project_files_processed:
                if st.sidebar.button(f"Process {project_type} Project"):
                    process_project(project_type, project_name, project_files)
            else:
                st.sidebar.success(f"{project_type} project '{project_name}' is loaded and ready for analysis.")
        
        # Project Tools section
        if st.session_state.get('current_project') and st.session_state.get('project_files_processed', False):
            st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)
            st.sidebar.subheader(f"Project Analysis Tools")
            
            tool_options = [
                "Analyze Project Structure",
                "Show Dependency Graph",
                "Visualize Project Structure",
                "Generate Class Diagram",
                "Show Project Summary"
            ]
            if project_type == "Java":
                tool_options.append("Show Java Project Analysis")
            
            selected_tool = st.sidebar.selectbox("Select Analysis Tool", tool_options)
            
            if st.sidebar.button("Run Analysis"):
                if selected_tool == "Analyze Project Structure":
                    analyze_project_structure(project_name, project_type.lower())
                elif selected_tool == "Show Dependency Graph":
                    show_dependency_graph(project_name, project_type.lower())
                elif selected_tool == "Visualize Project Structure":
                    visualize_project_structure(project_name, project_type.lower())
                elif selected_tool == "Generate Class Diagram":
                    generate_class_diagram(project_name, project_type.lower())
                elif selected_tool == "Show Project Summary":
                    show_project_summary(project_name, project_type.lower())
                elif selected_tool == "Show Java Project Analysis":
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
            
            # Check if a directory was uploaded
            if len(project_files) == 1 and project_files[0].type == "application/x-directory":
                project_dir = project_files[0].name
                directory_content = {"project_root": project_dir}
            else:
                # Process individual files
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
        try:
            structure = json.loads(result)
            st.json(structure)
            
            # Display some key metrics
            if 'file_count' in structure:
                st.metric("Total Files", structure['file_count'])
            if 'java_file_count' in structure:
                st.metric("Java Files", structure['java_file_count'])
            if 'packages' in structure:
                st.metric("Packages", len(structure['packages']))
            
            # Display file lists
            if 'source_files' in structure:
                with st.expander("Source Files"):
                    st.write(structure['source_files'])
            if 'test_files' in structure:
                with st.expander("Test Files"):
                    st.write(structure['test_files'])
            if 'config_files' in structure:
                with st.expander("Configuration Files"):
                    st.write(structure['config_files'])
            
        except json.JSONDecodeError:
            st.text(result)  # Fallback to displaying as plain text
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

def visualize_project_structure(project_name, project_type):
    llm_os = st.session_state.get("llm_os")
    if llm_os:
        code_tools = CodeTools(knowledge_base=llm_os.knowledge_base)
        result = code_tools.visualize_project_structure(project_name, project_type)
        st.image(f"{project_name}_structure.png")
        st.success(result)
    else:
        st.sidebar.error("LLM OS not initialized. Please try restarting the application.")

def generate_class_diagram(project_name, project_type):
    llm_os = st.session_state.get("llm_os")
    if llm_os:
        code_tools = CodeTools(knowledge_base=llm_os.knowledge_base)
        result = code_tools.generate_class_diagram(project_name, project_type)
        st.image(f"{project_name}_class_diagram.png")
        st.success(result)
    else:
        st.sidebar.error("LLM OS not initialized. Please try restarting the application.")

def show_project_summary(project_name, project_type):
    llm_os = st.session_state.get("llm_os")
    if llm_os:
        try:
            code_tools = CodeTools(knowledge_base=llm_os.knowledge_base)
            summary = code_tools.generate_project_summary(project_name, project_type)
            if summary:
                st.markdown(summary)
            else:
                st.warning("Unable to generate project summary. Please ensure the project is properly loaded.")
        except Exception as e:
            st.error(f"An error occurred while generating the project summary: {str(e)}")
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