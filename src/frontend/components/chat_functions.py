import streamlit as st

from .chat.business_analysis_chat import BusinessAnalysisChat
from .chat.general_chat import GeneralChat
from .chat.project_management_chat import ProjectManagementChat
from utils.icon_loader import load_org_icons

def render_chat(user_id, user_role, org_id):
    system_chat_icon, user_chat_icon = load_org_icons()

    general_chat = GeneralChat(system_chat_icon, user_chat_icon)
    general_chat.initialize_assistant(user_id, org_id, user_role, st.session_state.get("nickname", "friend"))
    general_chat.render_chat_interface(user_id, org_id, user_role, st.session_state.get("nickname", "friend"))

def render_project_management_chat(org_id, user_role):
    system_chat_icon, user_chat_icon = load_org_icons()

    pm_chat = ProjectManagementChat(system_chat_icon, user_chat_icon)
    pm_chat.render_chat_interface(org_id)
    
def render_business_analysis_chat(org_id, user_role):
    system_chat_icon, user_chat_icon = load_org_icons()

    ba_chat = BusinessAnalysisChat(system_chat_icon, user_chat_icon)
    ba_chat.render_chat_interface(org_id)    

def render_selected_chat(chat_type, user_id, user_role, org_id):
    if chat_type == 'general':
        render_chat(user_id, user_role, org_id)
    elif chat_type == 'project_management':
        render_project_management_chat(org_id, user_role)
    elif chat_type == 'business_analysis':
        render_business_analysis_chat(org_id, user_role)
    else:
        st.error(f"Invalid chat type: {chat_type}")