import streamlit as st
from components.chat import render_chat
from utils.auth import is_authenticated
from utils.helpers import setup_logging

logger = setup_logging()

def render_chat_page():
    if not is_authenticated():
        st.warning("Please log in to access the chat.")
        return

    st.markdown(
        """
        <style>
        .chat-container {
            display: flex;
            flex-direction: column;
            height: calc(100vh - 120px);  /* Adjust based on your layout */
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
        }
        .chat-input {
            margin-top: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="chat-messages">', unsafe_allow_html=True)
        render_chat(user_id=st.session_state.get('user_id'), user_role=st.session_state.get('role'))
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    render_chat_page()