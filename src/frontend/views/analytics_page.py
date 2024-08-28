import streamlit as st
from components.analytics_dashboard import render_analytics_dashboard
from utils.auth import is_authenticated
from utils.helpers import setup_logging

logger = setup_logging()

def render_analytics_page():
    if not is_authenticated():
        st.warning("Please log in to view analytics.")
        return

    if not st.session_state.get('is_admin', False):
        st.error("You do not have permission to view this page.")
        return

    render_analytics_dashboard()

if __name__ == "__main__":
    render_analytics_page()