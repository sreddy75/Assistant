import streamlit as st
import requests
from ui.components.utils import BACKEND_URL

def render_document_manager():
    st.header("My Uploaded Documents")
    if st.button("Refresh Document List"):
        response = requests.get(f"{BACKEND_URL}/api/user-documents", headers={"Authorization": f"Bearer {st.session_state['token']}"})
        if response.status_code == 200:
            st.session_state["user_documents"] = response.json()
        else:
            st.error("Failed to fetch user documents")
    
    user_documents = st.session_state.get("user_documents", [])
    if user_documents:
        for doc in user_documents:
            st.write(f"- {doc}")
    else:
        st.write("No documents uploaded yet.")