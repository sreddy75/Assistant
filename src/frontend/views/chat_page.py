import streamlit as st
from components.chat import render_chat
from utils.auth import is_authenticated
from utils.helpers import setup_logging

logger = setup_logging()

def render_chat_page():
    if not is_authenticated():
        st.warning("Please log in to access the chat.")
        return    

    with st.container():
        render_chat(user_id=st.session_state.get('user_id'), user_role=st.session_state.get('role'))


if __name__ == "__main__":
    render_chat_page()