import streamlit as st
from components.analytics_dashboard import render_analytics_dashboard
from utils.auth import is_authenticated
from utils.helpers import setup_logging

logger = setup_logging()

def render_home_page():
    if not is_authenticated():
        st.warning("Please log in to view the dashboard.")
        return
    
    # Render the analytics dashboard
    render_analytics_dashboard()

if __name__ == "__main__":
    render_home_page()