import streamlit as st
import requests
import json
import asyncio
from sseclient import SSEClient
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
        
        if 'assistant_id' not in st.session_state:
            response = requests.get(f"{BACKEND_URL}/api/v1/assistant/get-assistant", 
                                    params={"user_id": st.session_state.user_id,
                                            "org_id": st.session_state.org_id,
                                            "user_role": user_role,
                                            "user_nickname": st.session_state.nickname})
            if response.status_code == 200:
                st.session_state.assistant_id = response.json()["assistant_id"]
                st.sidebar.write(f"Debug: New Assistant ID = {st.session_state.assistant_id}")  # Debug line
            else:
                st.sidebar.error("Failed to get assistant. Please try reloading the page.")

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
    
    with st.sidebar:
        # User greeting
        user_nickname = st.session_state.get('nickname', 'User')
        st.header(f"Hello, :green[{user_nickname}] !", divider="red")
    
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
        with st.sidebar.expander("Code Assistant", expanded=False):                 
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

def process_project(project_type, project_name, project_files):
    progress_bar = st.sidebar.progress(0)
    status_text = st.sidebar.empty()

    try:
        directory_content = {
            file.name: file.read().decode('utf-8', errors='ignore')
            for file in project_files
        }

        assistant_id = st.session_state.get("assistant_id")
        if not assistant_id:
            st.sidebar.error("Assistant ID not found. Please make sure you're properly logged in.")
            return

        with st.spinner('Processing project...'):
            response = requests.post(
                f"{BACKEND_URL}/api/v1/assistant/load-project-stream",
                json={
                    "assistant_id": assistant_id,
                    "project_name": project_name,
                    "project_type": project_type.lower(),
                    "directory_content": directory_content
                },
                stream=True
            )

            client = SSEClient(response)
            for event in client.events():
                if event.data:
                    data = json.loads(event.data)
                    if 'error' in data:
                        st.sidebar.error(f"Error: {data['error']}")
                        break
                    if 'progress' in data:
                        progress_bar.progress(data['progress'])
                    if 'message' in data:
                        status_text.text(data['message'])
                    if data.get('status') == 'complete':
                        st.sidebar.success(data['message'])
                        st.session_state['current_project'] = project_name
                        st.session_state['current_project_type'] = project_type.lower()
                        st.session_state.project_files_processed = True
                        break

    except Exception as e:
        st.sidebar.error(f"Error processing {project_type} project files: {str(e)}")
    finally:
        progress_bar.empty()
        status_text.empty()

if __name__ == "__main__":
    render_sidebar()