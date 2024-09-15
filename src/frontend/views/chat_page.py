import streamlit as st
from components.chat import render_chat, render_project_management_chat
from utils.auth import is_authenticated, get_user_role
from utils.helpers import setup_logging

logger = setup_logging()

def render_chat_page():
    if not is_authenticated():
        st.warning("Please log in to access the chat.")
        return    

    with st.container():
        user_role = get_user_role()
    
        if user_role == "Super Admin" or user_role == "Manager":
            tab1, tab2 = st.tabs(["General Chat", "Project Management"])
            
            with tab1:
                render_chat(user_id=st.session_state.get('user_id'), user_role=user_role)
            
            with tab2:
                render_project_management_chat(org_id=st.session_state.get('org_id'), user_role=user_role)
        else:
            render_chat(user_id=st.session_state.get('user_id'), user_role=user_role)


if __name__ == "__main__":
    render_chat_page()