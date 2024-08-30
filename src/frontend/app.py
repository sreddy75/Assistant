import streamlit as st
from utils.auth import is_authenticated, login_form, logout
from styles.custom_theme import apply_custom_theme, maximize_content_area, apply_expander_style
from views.home_page import render_home_page
from views.chat_page import render_chat_page
from views.knowledge_base_page import render_knowledge_base_page
from views.analytics_page import render_analytics_page
from views.settings_page import render_settings_page
from components.sidebar_manager import render_sidebar
from utils.helpers import setup_logging

def main():
    setup_logging()
    apply_custom_theme()
    # maximize_content_area()
    apply_expander_style()

    if not is_authenticated():
        login_form()
    else:
        render_main_app()

def render_main_app():
    st.markdown(
        """
        <style>
        .main-container {
            display: flex;
            flex-direction: row;
        }
        .content-area {
            flex: 1;
            padding-right: 20px;
        }
        .sidebar-area {
            width: 300px;
            padding-left: 20px;
            border-left: 1px solid #ddd;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Initialize session state for navigation
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"

    # Navigation using tabs
    tabs = st.tabs(["Dashboard", "Chat", "Knowledge Base", "Analytics", "Settings"])

    st.markdown('<div class="main-container">', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-area">', unsafe_allow_html=True)
    render_sidebar()
    st.markdown('</div>', unsafe_allow_html=True)  # Close main-container
    
    # Main content area
    st.markdown('<div class="content-area">', unsafe_allow_html=True)
    
    with tabs[0]:
        st.session_state.current_page = "Dashboard"
        render_home_page()
    
    with tabs[1]:
        st.session_state.current_page = "Chat"
        render_chat_page()
    
    with tabs[2]:
        st.session_state.current_page = "Knowledge Base"
        render_knowledge_base_page()
    
    with tabs[3]:
        st.session_state.current_page = "Analytics"
        if st.session_state.get('is_admin', False):
            render_analytics_page()
        else:
            st.error("You don't have permission to access this page.")
    
    with tabs[4]:
        st.session_state.current_page = "Settings"
        if st.session_state.get('is_super_admin', False):
            render_settings_page()
        else:
            st.error("You don't have permission to access this page.")

    st.markdown('</div>', unsafe_allow_html=True)


    # Logout button
    if st.sidebar.button("Logout", key="logout_button"):        
        logout()
        st.rerun()

if __name__ == "__main__":
    main()