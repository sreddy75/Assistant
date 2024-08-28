import streamlit as st
from components.knowledge_base import render_knowledge_base
from utils.auth import is_authenticated
from utils.helpers import setup_logging

logger = setup_logging()

def render_knowledge_base_page():
    if not is_authenticated():
        st.warning("Please log in to access the knowledge base.")
        return

    render_knowledge_base()

if __name__ == "__main__":
    render_knowledge_base_page()