import streamlit as st
from components.settings_manager import (
    render_org_management,
    render_user_management,
    render_model_selection
)
from utils.auth import is_authenticated
    
def render_settings_page():
    if not is_authenticated():
        st.warning("Please log in to access the settings.")
        return

    if not st.session_state.get('is_super_admin'):
        st.error("You don't have permission to access this page.")
        return

    st.title("Settings")

    tab1, tab2, tab3 = st.tabs(["Organization Management", "User Management", "Model Selection"])

    with tab1:
        render_org_management()

    with tab2:
        render_user_management()

    with tab3:
        render_model_selection()

if __name__ == "__main__":
    render_settings_page()