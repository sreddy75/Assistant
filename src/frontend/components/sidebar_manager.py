import streamlit as st
import requests
import json
from utils.api import BACKEND_URL
from utils.helpers import restart_assistant
from config.settings import ENABLED_ASSISTANTS
from src.backend.db.session import get_db
from src.backend.models.models import Organization, OrganizationConfig
from components.settings_manager import render_model_selection
def initialize_session_state(user_role):
    org_id = st.session_state.get('org_id')
    if not org_id:
        st.error("Organization ID not found in session state.")
        return

    db = next(get_db())
    try:
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            st.error(f"Organization not found for ID: {org_id}")
            return

        org_config = db.query(OrganizationConfig).filter(OrganizationConfig.id == org.config_id).first()
        if not org_config:
            st.error(f"Organization config not found for org ID: {org_id}")
            return

        roles = json.loads(org_config.roles)
        assistants = json.loads(org_config.assistants)
        feature_flags = json.loads(org_config.feature_flags)

        role_assistants = assistants.get(user_role, [])

        for assistant in ENABLED_ASSISTANTS:
            key = f"{assistant.lower().replace(' ', '_')}_enabled"
            if key not in st.session_state:
                st.session_state[key] = assistant in role_assistants

        st.session_state['org_config'] = {
            'roles': roles,
            'assistants': assistants,
            'feature_flags': feature_flags
        }

    except Exception as e:
        st.error(f"Failed to load organization config: {str(e)}")
    finally:
        db.close()

def render_sidebar():
    user_role = st.session_state.get('role')
    if not user_role:
        st.sidebar.error("User role not found. Please log in again.")
        return    

    initialize_session_state(user_role)
    st.sidebar.markdown('<hr class="sidebar-separator">', unsafe_allow_html=True)

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

    if "Code Assistant" in available_assistants:        
        st.sidebar.markdown('<hr class="sidebar-separator">', unsafe_allow_html=True)
        st.sidebar.subheader("Project Management")

        project_type = st.sidebar.selectbox("Select Project Type", ["React", "Java"])
        project_name = st.sidebar.text_input("Enter Project Name")

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

        st.sidebar.markdown('<hr class="sidebar-separator">', unsafe_allow_html=True)
        
    render_model_selection            

def process_project(project_type, project_name, project_files):
    progress_bar = st.sidebar.progress(0)
    status_text = st.sidebar.empty()

    try:
        directory_content = {}
        total_files = len(project_files)

        for i, file in enumerate(project_files):
            file_content = file.read().decode('utf-8', errors='ignore')
            directory_content[file.name] = file_content

            progress = (i + 1) / total_files
            progress_bar.progress(progress)
            status_text.text(f"Processing file {i+1} of {total_files}: {file.name}")

        assistant_id = st.session_state.get("assistant_id")
        if not assistant_id:
            st.sidebar.error("Assistant ID not found. Please make sure you're properly logged in.")
            return

        response = requests.get(f"{BACKEND_URL}/api/v1/assistant/assistant-info/{assistant_id}")
        if response.status_code == 200:
            assistant_info = response.json()
            if assistant_info.get("has_knowledge_base"):
                run_response = requests.post(f"{BACKEND_URL}/api/v1/assistant/create-run", params={"assistant_id": assistant_id})
                if run_response.status_code == 200:
                    run_id = run_response.json().get("run_id")

                    load_project_response = requests.post(
                        f"{BACKEND_URL}/api/v1/assistant/load-project",
                        json={
                            "assistant_id": assistant_id,
                            "project_name": project_name,
                            "project_type": project_type.lower(),
                            "directory_content": directory_content
                        }
                    )

                    if load_project_response.status_code == 200:
                        result = load_project_response.json().get("result")
                        st.sidebar.success(result)
                        st.session_state['current_project'] = project_name
                        st.session_state['current_project_type'] = project_type.lower()
                        st.session_state.project_files_processed = True
                    else:
                        st.sidebar.error("Failed to load project. Please try again.")
                else:
                    st.sidebar.error("Failed to create a new run. Please try again.")
            else:
                st.sidebar.error("The assistant does not have a knowledge base initialized. Please try restarting the application.")
        else:
            st.sidebar.error("Failed to get assistant information. Please try again.")
    except Exception as e:
        st.sidebar.error(f"Error processing {project_type} project files: {str(e)}")
    finally:
        progress_bar.empty()
        status_text.empty()

if __name__ == "__main__":
    render_sidebar()