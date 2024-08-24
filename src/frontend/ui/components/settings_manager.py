from datetime import datetime, timedelta
import streamlit as st
import requests
from src.backend.core.config import settings
from ui.components.utils import restart_assistant

BACKEND_URL = settings.BACKEND_URL

def render_settings_tab():
    st.header("Settings")
    
    tab1, tab2, tab3 = st.tabs(["Organization Management", "User Management", "Model Selection"])
    
    with tab1:
        render_org_management()
    
    with tab2:
        render_user_management()
    
    with tab3:
        render_model_selection()

def render_org_management():
    st.subheader("Organization Management")

    # Fetch organizations
    response = requests.get(f"{BACKEND_URL}/api/v1/organizations", 
                            headers={"Authorization": f"Bearer {st.session_state.token}"})
    if response.status_code == 200:
        organizations = response.json()
        
        # Display existing organizations
        for org in organizations:
            st.write(f"Organization: {org.get('name', 'N/A')}")
            roles = org.get('roles', [])
            st.write(f"Roles: {', '.join(roles) if roles else 'No roles defined'}")
            
            # Edit organization
            new_org_name = st.text_input("New Name", key=f"edit_name_{org.get('id', 'unknown')}")
            new_org_roles = st.text_input("New Roles (comma-separated)", key=f"edit_roles_{org.get('id', 'unknown')}")
            
            if st.button("Update", key=f"update_{org.get('id', 'unknown')}"):
                update_data = {}
                if new_org_name:
                    update_data["name"] = new_org_name
                if new_org_roles:
                    update_data["roles"] = [role.strip() for role in new_org_roles.split(',')]
                
                if update_data:
                    update_response = requests.put(f"{BACKEND_URL}/api/v1/organizations/{org.get('id', 'unknown')}", 
                                                   json=update_data,
                                                   headers={"Authorization": f"Bearer {st.session_state.token}"})
                    if update_response.status_code == 200:
                        st.success("Organization updated successfully")
                    else:
                        st.error("Failed to update organization")
            
            # Delete organization
            if st.button("Delete", key=f"delete_{org.get('id', 'unknown')}"):
                delete_response = requests.delete(f"{BACKEND_URL}/api/v1/organizations/{org.get('id', 'unknown')}",
                                                  headers={"Authorization": f"Bearer {st.session_state.token}"})
                if delete_response.status_code == 200:
                    st.success("Organization deleted successfully")
                else:
                    st.error("Failed to delete organization")
            
            st.markdown("---")
        
        # Create new organization
        st.subheader("Create New Organization")
        new_org_name = st.text_input("Name", key="new_org_name")
        new_org_roles = st.text_input("Roles (comma-separated)", key="new_org_roles")
        
        if st.button("Create", key="create_org"):
            if new_org_name and new_org_roles:
                create_data = {
                    "name": new_org_name,
                    "roles": [role.strip() for role in new_org_roles.split(',')]
                }
                create_response = requests.post(f"{BACKEND_URL}/api/v1/organizations", 
                                                json=create_data,
                                                headers={"Authorization": f"Bearer {st.session_state.token}"})
                if create_response.status_code == 200:
                    st.success("New organization created successfully")
                else:
                    st.error("Failed to create new organization")
            else:
                st.warning("Please provide both name and roles for the new organization")
    else:
        st.error("Failed to fetch organizations")

def render_user_management():
    st.subheader("User Management")

    # Fetch users
    response = requests.get(f"{BACKEND_URL}/api/v1/users", 
                            headers={"Authorization": f"Bearer {st.session_state.token}"})
    if response.status_code == 200:
        users = response.json()
        
        # Display existing users
        for index, user in enumerate(users):
            st.write(f"User: {user.get('first_name', '')} {user.get('last_name', '')} ({user.get('nickname', 'N/A')})")
            st.write(f"Email: {user.get('email', 'N/A')}")
            st.write(f"Role: {user.get('role', 'N/A')}")
            st.write(f"Organization: {user.get('organization', 'N/A')}")
            st.write(f"Trial End Date: {user.get('trial_end', 'N/A')}")
            
            # Trial extension
            if user.get('role') == 'trial':
                days_to_extend = st.number_input(f"Extend trial for {user['nickname']} (days)", 
                                                 min_value=1, max_value=30, value=7, 
                                                 key=f"extend_trial_{user['id']}_{index}")
                if st.button(f"Extend Trial for {user['nickname']}", key=f"extend_button_{user['id']}_{index}"):
                    extend_response = requests.post(
                        f"{BACKEND_URL}/api/v1/users/{user['id']}/extend-trial",
                        json={"days": days_to_extend},
                        headers={"Authorization": f"Bearer {st.session_state.token}"}
                    )
                    if extend_response.status_code == 200:
                        st.success(f"Trial extended for {user['nickname']} by {days_to_extend} days")
                    else:
                        st.error(f"Failed to extend trial for {user['nickname']}")
            
            # Change user role
            new_role = st.selectbox(f"Change role for {user['nickname']}", 
                                    ['trial', 'user', 'admin'], 
                                    key=f"change_role_{user['id']}_{index}")
            if st.button(f"Update Role for {user['nickname']}", key=f"update_role_{user['id']}_{index}"):
                update_response = requests.put(
                    f"{BACKEND_URL}/api/v1/users/{user['id']}/role",
                    json={"role": new_role},
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
                if update_response.status_code == 200:
                    st.success(f"Role updated for {user['nickname']} to {new_role}")
                else:
                    st.error(f"Failed to update role for {user['nickname']}")
            
            # Delete user
            if st.button(f"Delete {user['nickname']}", key=f"delete_{user['id']}_{index}"):
                delete_response = requests.delete(
                    f"{BACKEND_URL}/api/v1/users/{user['id']}",
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
                if delete_response.status_code == 200:
                    st.success(f"User {user['nickname']} deleted successfully")
                else:
                    st.error(f"Failed to delete user {user['nickname']}")
            
            st.markdown("---")
        
        # Create new user
        st.subheader("Create New User")
        new_email = st.text_input("Email", key="new_email")
        new_password = st.text_input("Password", type="password", key="new_password")
        new_first_name = st.text_input("First Name", key="new_first_name")
        new_last_name = st.text_input("Last Name", key="new_last_name")
        new_nickname = st.text_input("Nickname", key="new_nickname")
        new_role = st.selectbox("Role", ['trial', 'user', 'admin'], key="new_role")
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
    st.subheader("Model Selection")

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