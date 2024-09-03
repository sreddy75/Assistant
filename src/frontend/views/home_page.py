import streamlit as st
from components.analytics_dashboard import (
        get_analytics_data, render_active_users, render_key_insights, render_interaction_metrics,
        render_quality_metrics
    )
from utils.auth import is_authenticated
from utils.helpers import setup_logging

logger = setup_logging()

def render_home_page():
    if not is_authenticated():
        st.warning("Please log in to view the dashboard.")
        return        

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
        # Render analytics dashboard
        st.header("Analytics Overview")
        col1, col2, col3 = st.columns(3)
        sentiment_analysis, feedback_analysis, user_engagement, interaction_metrics, quality_metrics, usage_patterns = get_analytics_data()        
        with col1:
            render_active_users(user_engagement)
        with col2:
            render_key_insights(user_engagement, interaction_metrics, quality_metrics, usage_patterns)
        with col3:
            render_interaction_metrics(interaction_metrics)
        
        render_quality_metrics(quality_metrics, sentiment_analysis)    
    
    st.divider()
    
    # Recent Activity
    # with st.expander(label="System Status", expanded=False, icon=":material/activity:"):
        # st.subheader("Recent Activity")
        # activities = [
        #     "Uploaded new document: 'Project Proposal.pdf'",
        #     "Completed chat session with Code Assistant",
        #     "Updated user profile information",
        #     "Analyzed data set using Data Analyst",
        #     "Started new project: 'Web App Redesign'"
        # ]
        # for activity in activities:
        #     st.write(f"• {activity}")
    
    # st.divider()        
    
    with st.expander(label="System Status", expanded=False):
    # System Status
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