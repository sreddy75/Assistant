from datetime import datetime, timedelta
import json
import pandas as pd
import streamlit as st
import io
from PIL import Image
import requests
from src.backend.core.config import settings
from ui.components.utils import restart_assistant

BACKEND_URL = settings.BACKEND_URL
import json
import pandas as pd
import streamlit as st
import io
from PIL import Image
import requests
from src.backend.core.config import settings
from ui.components.utils import restart_assistant

BACKEND_URL = settings.BACKEND_URL
    
def render_settings_tab():
    
    tab1, tab2, tab3 = st.tabs(["Organization Management", "User Management", "Model Selection"])
    
    with tab1:
        render_org_management()
    
    with tab2:
        render_user_management()
    
    with tab3:
        render_model_selection()

def render_org_management():

    # Fetch organizations
    response = requests.get(f"{BACKEND_URL}/api/v1/organizations", 
                            headers={"Authorization": f"Bearer {st.session_state.token}"})
    if response.status_code == 200:
        organizations = response.json()
        
        if organizations:
            # Create DataFrame for organization table
            df = pd.DataFrame(organizations)
            df['Select'] = False
            
            # Display the table with checkboxes
            edited_df = st.data_editor(
                df[["id", "name", "roles", "Select"]],
                hide_index=True,
                column_config={
                    "Select": st.column_config.CheckboxColumn(
                        "Select",
                        help="Select to edit or delete"
                    )
                },
                disabled=["id", "name", "roles"]
            )
            
            # Get the selected organization
            selected_orgs = edited_df[edited_df['Select']].to_dict('records')
            
            if len(selected_orgs) == 1:
                selected_org = selected_orgs[0]
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Edit Selected"):
                        st.session_state.editing_org_id = selected_org['id']
                        st.rerun()
                with col2:
                    if st.button("Delete Selected"):
                        delete_organization(selected_org['id'])
                        st.rerun()                                
                
            elif len(selected_orgs) > 1:
                st.warning("Please select only one organization to edit or delete.")
        else:
            st.info("No organizations found.")
        
        
        # Create or Edit Organization
        if "editing_org_id" in st.session_state:
            st.subheader(f"Edit Organization (ID: {st.session_state.editing_org_id})")
            org_to_edit = next((org for org in organizations if org["id"] == st.session_state.editing_org_id), None)
            if org_to_edit:
                create_or_edit_organization(org_to_edit)
            else:
                st.error("Selected organization not found.")
        else:
            st.subheader("Create New Organization")
            create_or_edit_organization(None)

    else:
        st.error(f"Failed to fetch organizations. Status code: {response.status_code}")

def display_org_assets(org_id):
    asset_types = ["chat_system_icon", "chat_user_icon", "main_image"]
    for asset_type in asset_types:
        response = requests.get(f"{BACKEND_URL}/api/v1/organizations/asset/{org_id}/{asset_type}", 
                                headers={"Authorization": f"Bearer {st.session_state.token}"})
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content))
            st.image(image, caption=f"{asset_type.replace('_', ' ').title()}")
        else:
            st.warning(f"Failed to load {asset_type}")
    
    for file_type in ["instructions", "config_toml"]:
        response = requests.get(f"{BACKEND_URL}/api/v1/organizations/asset/{org_id}/{file_type}",
                                headers={"Authorization": f"Bearer {st.session_state.token}"})
        if response.status_code == 200:
            st.download_button(
                label=f"Download {file_type.replace('_', ' ').title()}",
                data=response.content,
                file_name=f"{file_type}.{'json' if file_type == 'instructions' else 'toml'}",
                mime=f"application/{'json' if file_type == 'instructions' else 'toml'}"
            )
        else:
            st.warning(f"Failed to load {file_type}")

def create_or_edit_organization(org=None):
    is_editing = org is not None
    
    name = st.text_input("Name", value=org.get("name", "") if is_editing else "")
    
    # Define asset types and their display names
    asset_types = [
        ("roles", "Roles"),
        ("assistants", "Assistants"),
        ("instructions", "Instructions (JSON)"),
        ("config_toml", "Config (TOML)"),
        ("chat_system_icon", "Chat System Icon"),
        ("chat_user_icon", "Chat User Icon"),
        ("main_image", "Main Image"),
        ("feature_flags", "Feature Flags")
    ]
    
    # Create a dictionary to store uploaded files and JSON data
    new_files = {}
    json_data = {}
    
    for asset_type, display_name in asset_types:
        with st.expander(f"{display_name}", expanded=False):
            col1, col2 = st.columns([0.7, 0.3])
            
            with col1:                
                if is_editing:
                    response = requests.get(f"{BACKEND_URL}/api/v1/organizations/asset/{org['id']}/{asset_type}", 
                                            headers={"Authorization": f"Bearer {st.session_state.token}"})
                    if response.status_code == 200:
                        if asset_type in ["chat_system_icon", "chat_user_icon", "main_image"]:
                            image = Image.open(io.BytesIO(response.content))
                            st.image(image, caption=display_name, width=200)
                        elif asset_type == "roles":
                            roles_data = response.json()
                            if roles_data:
                                st.write("Current Roles:")
                                st.write(", ".join(roles_data))
                            else:
                                st.info("No roles set")
                        elif asset_type in ["assistants", "feature_flags"]:
                            data = response.json()
                            if data:
                                st.json(data)
                            else:
                                st.info(f"No {display_name.lower()} set")
                        else:
                            st.download_button(
                                label=f"Download {display_name}",
                                data=response.content,
                                file_name=f"{asset_type}.{'json' if asset_type in ['instructions', 'assistants'] else 'toml'}",
                                mime=f"application/{'json' if asset_type in ['instructions', 'assistants'] else 'toml'}"
                            )
                    else:
                        st.warning(f"No current {display_name}")                
                else:
                    st.info(f"No current {display_name}")
            
            with col2:
                if asset_type == "roles":
                    roles_input = st.text_area(f"Enter {display_name} (comma-separated)", 
                                               key=f"input_{asset_type}",
                                               help="Enter roles as a comma-separated list, e.g., 'Dev, QA, Manager, Admin, Super Admin'")
                    if roles_input:
                        roles_list = [role.strip() for role in roles_input.split(',') if role.strip()]
                        json_data[asset_type] = roles_list
                        st.success(f"Roles ready to update: {', '.join(roles_list)}")
                elif asset_type in ["chat_system_icon", "chat_user_icon", "main_image"]:
                    uploaded_file = st.file_uploader(f"Upload {display_name}", type="png", key=f"upload_{asset_type}")
                    if uploaded_file:
                        new_files[asset_type] = uploaded_file
                        st.image(uploaded_file, caption=f"New {display_name}", width=100)
                elif asset_type in ["feature_flags", "assistants"]:
                    uploaded_file = st.file_uploader(f"Upload {display_name}", type="json", key=f"upload_{asset_type}")
                    if uploaded_file:
                        try:
                            content = uploaded_file.read()
                            if not content:
                                st.error(f"{display_name} file is empty")
                            else:
                                json_content = json.loads(content)
                                json_data[asset_type] = json_content
                                st.json(json_content)
                        except json.JSONDecodeError:
                            st.error(f"Invalid JSON in {display_name} file")
                        finally:
                            uploaded_file.seek(0)  # Reset file pointer
                else:
                    uploaded_file = st.file_uploader(f"Upload {display_name}", 
                                                     type="json" if asset_type == "instructions" else "toml", 
                                                     key=f"upload_{asset_type}")
                    if uploaded_file:
                        new_files[asset_type] = uploaded_file
                        st.success(f"New {display_name} ready to upload")

        st.divider()
        
    if st.button("Update" if is_editing else "Create"):
        data = {
            "name": name,
        }
        
        # Add JSON data to the request
        for key, value in json_data.items():
            data[key] = json.dumps(value)
        
        with st.spinner("Processing..."):
            if is_editing:
                response = requests.put(
                    f"{BACKEND_URL}/api/v1/organizations/{org['id']}",
                    data=data,
                    files=new_files,
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
                success_message = "Organization updated successfully"
                error_message = "Failed to update organization"
            else:
                response = requests.post(
                    f"{BACKEND_URL}/api/v1/organizations",
                    data=data,
                    files=new_files,
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
                success_message = "New organization created successfully"
                error_message = "Failed to create new organization"
        
        if response.status_code == 200:
            st.success(success_message)
            if is_editing:
                del st.session_state.editing_org_id
            st.rerun()
        else:
            st.error(f"{error_message}: {response.text}")
            st.error("Please check the entered data and try again.")
    
    if is_editing:
        if st.button("Cancel Editing"):
            del st.session_state.editing_org_id
            st.rerun()

def delete_organization(org_id):
    if st.button(f"Confirm deletion of Organization (ID: {org_id})"):
        delete_response = requests.delete(
            f"{BACKEND_URL}/api/v1/organizations/{org_id}",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        if delete_response.status_code == 200:
            st.success(f"Organization (ID: {org_id}) deleted successfully")
        else:
            st.error(f"Failed to delete organization (ID: {org_id}): {delete_response.text}")
        
def render_user_management():
    st.subheader("User Management")

    # Fetch users
    response = requests.get(f"{BACKEND_URL}/api/v1/users", 
                            headers={"Authorization": f"Bearer {st.session_state.token}"})
    if response.status_code == 200:
        users = response.json()
        
def render_user_management():
    st.subheader("User Management")

    # Fetch users
    response = requests.get(f"{BACKEND_URL}/api/v1/users", 
                            headers={"Authorization": f"Bearer {st.session_state.token}"})
    if response.status_code == 200:
        users = response.json()
        
        # Create a DataFrame for the user table
        user_data = []
        for user in users:
            user_data.append({
                "ID": user.get('id'),
                "Name": f"{user.get('first_name', '')} {user.get('last_name', '')}",
                "Nickname": user.get('nickname', 'N/A'),
                "Email": user.get('email', 'N/A'),
                "Role": user.get('role', 'N/A'),
                "Organization": user.get('organization', 'N/A'),
                "Trial End": user.get('trial_end', 'N/A')
            })
        
        df = pd.DataFrame(user_data)
        
        # Display the user table
        st.dataframe(df)

        # User actions
        st.subheader("User Actions")
        selected_user = st.selectbox("Select a user", df['Nickname'])
        user = next((u for u in users if u['nickname'] == selected_user), None)

        if user:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                new_role = st.selectbox(f"Change role for {user['nickname']}", ['trial', 'user', 'admin'])
                if st.button(f"Update Role"):
                    update_response = requests.put(
                        f"{BACKEND_URL}/api/v1/users/{user['id']}/role",
                        json={"role": new_role},
                        headers={"Authorization": f"Bearer {st.session_state.token}"}
                    )
                    if update_response.status_code == 200:
                        st.success(f"Role updated for {user['nickname']} to {new_role}")
                    else:
                        st.error(f"Failed to update role for {user['nickname']}")

            with col2:
                if user.get('role') == 'trial':
                    days_to_extend = st.number_input(f"Extend trial for {user['nickname']} (days)", 
                                                     min_value=1, max_value=30, value=7)
                    if st.button(f"Extend Trial"):
                        extend_response = requests.post(
                            f"{BACKEND_URL}/api/v1/users/{user['id']}/extend-trial",
                            json={"days": days_to_extend},
                            headers={"Authorization": f"Bearer {st.session_state.token}"}
                        )
                        if extend_response.status_code == 200:
                            st.success(f"Trial extended for {user['nickname']} by {days_to_extend} days")
                        else:
                            st.error(f"Failed to extend trial for {user['nickname']}")
                else:
                    st.write("User is not on trial")

            with col3:
                if st.button(f"Delete User"):
                    delete_response = requests.delete(
                        f"{BACKEND_URL}/api/v1/users/{user['id']}",
                        headers={"Authorization": f"Bearer {st.session_state.token}"}
                    )
                    if delete_response.status_code == 200:
                        st.success(f"User {user['nickname']} deleted successfully")
                    else:
                        st.error(f"Failed to delete user {user['nickname']}")

        # Create new user
        st.subheader("Create New User")
        new_email = st.text_input("Email", key="new_email")
        new_password = st.text_input("Password", type="password", key="new_password")
        new_first_name = st.text_input("First Name", key="new_first_name")
        new_last_name = st.text_input("Last Name", key="new_last_name")
        new_nickname = st.text_input("Nickname", key="new_nickname")
        new_role = st.selectbox("Role", ['user', 'admin'], key="new_role")
        new_org = st.text_input("Organization", key="new_org")
        
        if st.button("Create User", key="create_user"):
            if new_email and new_password and new_first_name and new_last_name and new_nickname and new_role and new_org:
                create_data = {
                    "email": new_email,
                    "password": new_password,
                    "first_name": new_first_name,
                    "last_name": new_last_name,
                    "nickname": new_nickname,
                    "role": new_role,
                    "organization": new_org,
                    "trial_end": (datetime.now() + timedelta(days=7)).isoformat() if new_role == 'trial' else None
                }
                create_response = requests.post(f"{BACKEND_URL}/api/v1/users", 
                                                json=create_data,
                                                headers={"Authorization": f"Bearer {st.session_state.token}"})
                if create_response.status_code == 200:
                    st.success("New user created successfully")
                else:
                    st.error("Failed to create new user")
            else:
                st.warning("Please provide all required fields for the new user")
    else:
        st.error("Failed to fetch users")


def render_model_selection():
    with st.expander("Select model:", expanded=True):
        model_type = st.radio("Select Model Type", ["Closed", "Open Source"])

        if model_type == "Closed":
            llm_options = ["gpt-4o", "claude-3.5"]
            llm_id = st.selectbox("Select Closed Source Model", options=llm_options)
        else: 
            llm_options = ["llama3", "tinyllama"]
            llm_id = st.selectbox("Select Open Source Model", options=llm_options)
        
        if "llm_id" not in st.session_state:
            st.session_state["llm_id"] = llm_id
        elif st.session_state["llm_id"] != llm_id:
            st.session_state["llm_id"] = llm_id
            restart_assistant()

if __name__ == "__main__":
    render_settings_tab()