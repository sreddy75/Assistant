import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
from src.frontend.utils.api_helpers import update_azure_devops_schema
from utils.api import BACKEND_URL
from utils.helpers import handle_response
from src.frontend.utils.helpers import restart_assistant
from utils.helpers import send_event

def render_org_management():
    st.header("Organization Management")
    response = requests.get(f"{BACKEND_URL}/api/v1/organizations", 
                            headers={"Authorization": f"Bearer {st.session_state.token}"})
    if response.status_code == 200:
        organizations = response.json()

        if organizations:
            df = pd.DataFrame(organizations)
            df['Select'] = False

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

            selected_orgs = edited_df[edited_df['Select']].to_dict('records')

            if len(selected_orgs) == 1:
                selected_org = selected_orgs[0]
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Edit Selected"):
                        st.session_state.editing_org_id = selected_org['id']
                        st.rerun()
                    if st.button("Update Azure DevOps Schema"):
                        try:
                            result = update_azure_devops_schema()
                            st.success("Azure DevOps schema updated successfully")
                        except Exception as e:
                            st.error(f"Failed to update Azure DevOps schema: {str(e)}")
                with col2:
                    if st.button("Delete Selected"):
                        delete_organization(selected_org['id'])
                        st.rerun()

            elif len(selected_orgs) > 1:
                st.warning("Please select only one organization to edit or delete.")
        else:
            st.info("No organizations found.")

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

def create_or_edit_organization(org=None):
    is_editing = org is not None

    name = st.text_input("Name", value=org.get("name", "") if is_editing else "")

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

    new_files = {}
    json_data = {}

    for asset_type, display_name in asset_types:
        with st.expander(f"{display_name}", expanded=False):
            col1, col2 = st.columns([0.7, 0.3])

            with col1:                
                if is_editing:
                    display_current_asset(org['id'], asset_type, display_name)
                else:
                    st.info(f"No current {display_name}")

            with col2:
                handle_asset_upload(asset_type, display_name, new_files, json_data)

    # Add Azure DevOps Configuration
    with st.expander("Azure DevOps Configuration", expanded=True):
        if is_editing:
            azure_devops_config = get_azure_devops_config(org['id'])
        else:
            azure_devops_config = {"organization_url": "", "personal_access_token": "", "project": ""}

        azure_devops_url = st.text_input("Azure DevOps URL", value=azure_devops_config.get("organization_url", ""))
        azure_devops_token = st.text_input("Azure DevOps Personal Access Token", type="password")        

        json_data["azure_devops_config"] = {
            "organization_url": azure_devops_url,
            "personal_access_token": azure_devops_token if azure_devops_token else None
        }

    if st.button("Update" if is_editing else "Create"):
        update_or_create_organization(is_editing, org['id'] if is_editing else None, name, json_data, new_files)
        send_event("organization_updated" if is_editing else "organization_created", {"org_id": org['id'] if is_editing else None})


    if is_editing and st.button("Cancel Editing"):
        del st.session_state.editing_org_id
        st.rerun()

def display_current_asset(org_id, asset_type, display_name):
    response = requests.get(f"{BACKEND_URL}/api/v1/organizations/asset/{org_id}/{asset_type}", 
                            headers={"Authorization": f"Bearer {st.session_state.token}"})
    if response.status_code == 200:
        if asset_type in ["chat_system_icon", "chat_user_icon", "main_image"]:
            image = Image.open(BytesIO(response.content))
            st.image(image, caption=display_name, width=200)
        elif asset_type in ["roles", "assistants", "feature_flags"]:
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
    elif response.status_code == 404:
        st.warning(f"No current {display_name}")
    else:
        st.error(f"Failed to fetch {display_name}: {response.text}")

def handle_asset_upload(asset_type, display_name, new_files, json_data):
    if asset_type in ["roles", "assistants", "feature_flags"]:
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
    elif asset_type in ["chat_system_icon", "chat_user_icon", "main_image"]:
        uploaded_file = st.file_uploader(f"Upload {display_name}", type="png", key=f"upload_{asset_type}")
        if uploaded_file:
            new_files[asset_type] = uploaded_file
            st.image(uploaded_file, caption=f"New {display_name}", width=100)
    else:
        uploaded_file = st.file_uploader(f"Upload {display_name}", 
                                         type="json" if asset_type == "instructions" else "toml", 
                                         key=f"upload_{asset_type}")
        if uploaded_file:
            new_files[asset_type] = uploaded_file
            st.success(f"New {display_name} ready to upload")

def update_or_create_organization(is_editing, org_id, name, json_data, new_files):
    data = {"name": name}
    for key, value in json_data.items():
        data[key] = json.dumps(value)

    with st.spinner("Processing..."):
        if is_editing:
            response = requests.put(
                f"{BACKEND_URL}/api/v1/organizations/{org_id}",
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

def get_azure_devops_config(org_id):
    response = requests.get(f"{BACKEND_URL}/api/v1/organizations/azure-devops-config/{org_id}", 
                            headers={"Authorization": f"Bearer {st.session_state.token}"})
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        st.warning("Azure DevOps is not configured for this organization.")
        return {"organization_url": "", "project": ""}
    else:
        st.error(f"Failed to fetch Azure DevOps configuration: {response.text}")
        return {"organization_url": "", "project": ""}

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
    st.header("User Management")
    response = requests.get(f"{BACKEND_URL}/api/v1/users", 
                            headers={"Authorization": f"Bearer {st.session_state.token}"})
    if response.status_code == 200:
        users = response.json()
        user_data = [
            {
                "ID": user.get('id'),
                "Name": f"{user.get('first_name', '')} {user.get('last_name', '')}",
                "Nickname": user.get('nickname', 'N/A'),
                "Email": user.get('email', 'N/A'),
                "Role": user.get('role', 'N/A'),
                "Organization": user.get('organization', 'N/A'),
                "Trial End": user.get('trial_end', 'N/A')
            } for user in users
        ]

        df = pd.DataFrame(user_data)
        st.dataframe(df)

        st.subheader("User Actions")
        selected_user = st.selectbox("Select a user", df['Nickname'])
        user = next((u for u in users if u['nickname'] == selected_user), None)

        if user:
            col1, col2, col3 = st.columns(3)

            with col1:
                new_role = st.selectbox(f"Change role for {user['nickname']}", ['trial', 'user', 'admin'])
                if st.button(f"Update Role"):
                    update_user_role(user['id'], new_role)
                    send_event("user_role_updated", {"user_id": user['id'], "new_role": new_role})


            with col2:
                if user.get('role') == 'trial':
                    days_to_extend = st.number_input(f"Extend trial for {user['nickname']} (days)", 
                                                     min_value=1, max_value=30, value=7)
                    if st.button(f"Extend Trial"):
                        extend_user_trial(user['id'], days_to_extend)
                        send_event("user_trial_extended", {"user_id": user['id'], "days_extended": days_to_extend})

                else:
                    st.write("User is not on trial")

            with col3:
                if st.button(f"Delete User"):
                    delete_user(user['id'])
                    send_event("user_deleted", {"user_id": user['id']})


        st.subheader("Create New User")
        new_email = st.text_input("Email", key="new_email")
        new_password = st.text_input("Password", type="password", key="new_password")
        new_first_name = st.text_input("First Name", key="new_first_name")
        new_last_name = st.text_input("Last Name", key="new_last_name")
        new_nickname = st.text_input("Nickname", key="new_nickname")
        new_role = st.selectbox("Role", ['user', 'admin'], key="new_role")
        new_org = st.text_input("Organization", key="new_org")

        if st.button("Create User", key="create_user"):
            create_new_user(new_email, new_password, new_first_name, new_last_name, new_nickname, new_role, new_org)
            send_event("user_created", {"email": new_email, "role": new_role, "organization": new_org})

    else:
        st.error("Failed to fetch users")

def update_user_role(user_id, new_role):
    update_response = requests.put(
        f"{BACKEND_URL}/api/v1/users/{user_id}/role",
        json={"role": new_role},
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    if update_response.status_code == 200:
        st.success(f"Role updated to {new_role}")
    else:
        st.error(f"Failed to update role")

def extend_user_trial(user_id, days):
    extend_response = requests.post(
        f"{BACKEND_URL}/api/v1/users/{user_id}/extend-trial",
        json={"days": days},
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    if extend_response.status_code == 200:
        st.success(f"Trial extended by {days} days")
    else:
        st.error(f"Failed to extend trial")

def delete_user(user_id):
    delete_response = requests.delete(
        f"{BACKEND_URL}/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    if delete_response.status_code == 200:
        st.success(f"User deleted successfully")
    else:
        st.error(f"Failed to delete user")

def create_new_user(email, password, first_name, last_name, nickname, role, org):
    if email and password and first_name and last_name and nickname and role and org:
        create_data = {
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "nickname": nickname,
            "role": role,
            "organization": org,
            "trial_end": (datetime.now() + timedelta(days=7)).isoformat() if role == 'trial' else None
        }
        create_response = requests.post(
            f"{BACKEND_URL}/api/v1/users", 
            json=create_data,
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        if create_response.status_code == 200:
            st.success("New user created successfully")
            st.rerun()  # Refresh the page to show the new user in the list
        else:
            st.error(f"Failed to create new user: {create_response.text}")
    else:
        st.warning("Please provide all required fields for the new user")

def render_model_selection():
    st.header("Model Selection")
    
    with st.expander("Select model:", expanded=True):
        model_type = st.radio("Select Model Type", ["Closed", "Open Source"])

        if model_type == "Closed":
            llm_options = ["gpt-4", "claude-3.5"]
            llm_id = st.selectbox("Select Closed Source Model", options=llm_options)
        else: 
            llm_options = ["llama3.1"]
            llm_id = st.selectbox("Select Open Source Model", options=llm_options)

        if "llm_id" not in st.session_state:
            st.session_state["llm_id"] = llm_id
        elif st.session_state["llm_id"] != llm_id:
            st.session_state["llm_id"] = llm_id
            if st.button("Apply Model Change"):
                with st.spinner("Restarting assistant with new model..."):
                    restart_assistant()
                st.success("Model changed successfully. Assistant restarted.")
                send_event("model_changed", {"new_model": llm_id})


        st.info(f"Currently selected model: {st.session_state['llm_id']}")

    # Additional model-specific settings
    if llm_id in ["gpt-4", "claude-3.5"]:
        st.subheader("Advanced Settings")
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
        max_tokens = st.number_input("Max Tokens", min_value=1, max_value=8192, value=4096, step=1)
        
        if st.button("Update Advanced Settings"):
            # Here you would typically send these settings to your backend
            st.success("Advanced settings updated successfully.")
            send_event("advanced_settings_updated", {"temperature": temperature, "max_tokens": max_tokens})


    # Model performance metrics
    st.subheader("Model Performance")
    col1, col2, col3 = st.columns(3)
    col1.metric("Average Response Time", "0.8s")
    col2.metric("Accuracy Score", "95%")
    col3.metric("User Satisfaction", "4.7/5")

    # Usage statistics
    st.subheader("Usage Statistics")
    usage_data = {
        'Date': ['2024-08-01', '2024-08-02', '2024-08-03', '2024-08-04', '2024-08-05'],
        'Queries': [100, 120, 80, 150, 130]
    }
    usage_df = pd.DataFrame(usage_data)
    st.line_chart(usage_df.set_index('Date'))

    # Disclaimer
    st.markdown("---")
    st.caption("Note: Changing the model may affect the assistant's performance and capabilities. Please refer to the documentation for more details on each model.")