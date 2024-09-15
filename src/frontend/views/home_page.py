import streamlit as st
from components.analytics_dashboard import (
    get_analytics_data, render_active_users, render_key_insights, render_interaction_metrics,
    render_quality_metrics
)
from utils.auth import is_authenticated
from utils.helpers import setup_logging
import json

logger = setup_logging()

def render_home_page(org_config):
    if not is_authenticated():
        st.warning("Please log in to view the dashboard.")
        return        

    # Display org name if available
    org_name = org_config.get('name', 'Your Organization')
    st.title(f"Welcome to {org_name}")

    # Quick stats
    with st.expander(label="Quick stats", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Active Chats", value="5", delta="-2")
        with col2:
            st.metric(label="Knowledge Base Documents", value="42")
        with col3:
            st.metric(label="Tasks Completed Today", value="12")

    st.divider()
    
    with st.expander(label="Analytics", expanded=False):
        st.header("Analytics Overview")
        col1, col2, col3 = st.columns(3)
        analytics_data = get_analytics_data()
        
        if isinstance(analytics_data, str):
            try:
                analytics_data = json.loads(analytics_data)
            except json.JSONDecodeError:
                st.warning("Analytics data is not available at the moment. Please try again later.")
                analytics_data = {}

        if not analytics_data:
            st.warning("No analytics data available. This might be due to a configuration issue or lack of data.")
        else:
            sentiment_analysis = analytics_data.get('sentiment_analysis', {})
            feedback_analysis = analytics_data.get('feedback_analysis', {})
            user_engagement = analytics_data.get('user_engagement', {})
            interaction_metrics = analytics_data.get('interaction_metrics', {})
            quality_metrics = analytics_data.get('quality_metrics', {})
            usage_patterns = analytics_data.get('usage_patterns', {})

            with col1:
                render_active_users(user_engagement)
            with col2:
                combined_data = {
                    'user_engagement': user_engagement,
                    'interaction_metrics': interaction_metrics,
                    'quality_metrics': quality_metrics,
                    'usage_patterns': usage_patterns
                }
                render_key_insights(combined_data)
            with col3:
                render_interaction_metrics(interaction_metrics)
            
            render_quality_metrics(analytics_data)

    st.divider()
        
    with st.expander(label="System Status", expanded=False):
        st.subheader("System Status")
        system_status = {
            "AI Models": "Operational",
            "Database": "Operational",
            "API Services": "Operational",
            "File Storage": "Operational"
        }
        status_color = {"Operational": "green", "Degraded": "orange", "Down": "red"}
        for component, status in system_status.items():
            st.markdown(f"**{component}:** :{status_color[status]}[{status}]")

    st.divider()       
    
    # Tips or Help Section
    with st.expander(label="Tips & Help", expanded=False):
        st.markdown("""
        - Use the sidebar to navigate between different sections of the app.
        - You can start a new chat from the 'Chat' page.
        - Upload documents to the knowledge base to enhance your AI's capabilities.
        - Check the 'Analytics' page for detailed insights into your usage.
        - If you need help, click on the '?' icon in the top-right corner of any page.
        """)
        
    st.divider()        

if __name__ == "__main__":
    render_home_page()