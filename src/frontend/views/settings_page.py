import streamlit as st
from components.settings_manager import render_settings_tab
from utils.auth import is_authenticated
from utils.helpers import setup_logging

logger = setup_logging()

def render_settings_page():
    if not is_authenticated():
        st.warning("Please log in to access settings.")
        return

    if not st.session_state.get('is_super_admin', False):
        st.error("You do not have permission to view this page.")
        return
    
    render_settings_tab()

if __name__ == "__main__":
    render_settings_page()