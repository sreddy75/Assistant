import streamlit as st
import requests
from utils import BACKEND_URL

def render_settings_tab():
    st.header("Settings")
    # Add your settings management code here
    # This could include user management, organization settings, etc.
    # Example:
    if st.button("Fetch Users"):
        response = requests.get(f"{BACKEND_URL}/api/users", headers={"Authorization": f"Bearer {st.session_state['token']}"})
        if response.status_code == 200:
            users = response.json()
            st.write(users)
        else:
            st.error("Failed to fetch users")