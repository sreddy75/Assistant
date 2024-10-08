import streamlit as st
from components.chat_functions import render_chat, render_project_management_chat
from components.chat.business_analysis_chat import BusinessAnalysisChat
from src.frontend.components.chat.general_chat import GeneralChat
from src.frontend.components.chat.project_management_chat import ProjectManagementChat
from utils.auth import is_authenticated, get_user_role 
from src.frontend.utils.icon_loader import load_org_icons
from utils.helpers import setup_logging

logger = setup_logging()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_get_user_role():
    return get_user_role()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_load_org_icons():
    return load_org_icons()

def render_chat_page():
    if not is_authenticated():
        st.warning("Please log in to access the chat.")
        return    

    with st.container():
        user_id = st.session_state.get('user_id')
        org_id = st.session_state.get('org_id')
        user_role = cached_get_user_role()
    
        if user_role in ["Super Admin", "Manager"]:
            tab1, tab2, tab3 = st.tabs(["General Chat", "Project Management", "Business Analysis"])
            
            with tab1:
                if 'general_chat' not in st.session_state:
                    system_chat_icon, user_chat_icon = cached_load_org_icons()
                    st.session_state.general_chat = GeneralChat(system_chat_icon, user_chat_icon)
                st.session_state.general_chat.render_chat_interface(user_id, org_id, user_role, st.session_state.get("nickname", "friend"))
            
            with tab2:
                if 'pm_chat' not in st.session_state:
                    system_chat_icon, user_chat_icon = cached_load_org_icons()
                    st.session_state.pm_chat = ProjectManagementChat(system_chat_icon, user_chat_icon)
                st.session_state.pm_chat.render_chat_interface(org_id)
            
            with tab3:
                if 'ba_chat' not in st.session_state:
                    st.session_state.ba_chat = BusinessAnalysisChat(
                        system_chat_icon="🧠",
                        user_chat_icon="👤"
                    )
                st.session_state.ba_chat.render_chat_interface(org_id=org_id)
        else:
            if 'general_chat' not in st.session_state:
                system_chat_icon, user_chat_icon = cached_load_org_icons()
                st.session_state.general_chat = GeneralChat(system_chat_icon, user_chat_icon)
            st.session_state.general_chat.render_chat_interface(user_id, org_id, user_role, st.session_state.get("nickname", "friend"))

if __name__ == "__main__":
    render_chat_page()