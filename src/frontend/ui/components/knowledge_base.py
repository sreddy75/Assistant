import streamlit as st
import requests
import json
import pandas as pd
from src.backend.core.config import settings

BACKEND_URL = settings.BACKEND_URL

def knowledge_base_page():        
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Add Content", "Search Documents", "Manage Documents"])

    with tab1:
        add_content()

    with tab2:
        search_documents()

    with tab3:
        manage_documents()

def add_content():    

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Upload File")
        uploaded_file = st.file_uploader("Choose a file", type=['txt', 'pdf', 'docx', 'csv', 'xlsx'], key="kb_file_uploader")
        if uploaded_file:
            st.write(f"Selected file: {uploaded_file.name}")
            if st.button("Upload File", key="kb_upload_file_button"):
                upload_file(uploaded_file)

    with col2:
        st.subheader("Add URL")
        input_url = st.text_input("Enter URL", key="kb_url_input")
        if st.button("Add URL", key="kb_add_url_button"):
            add_url(input_url)

def search_documents():    
    search_query = st.text_input("Enter search query", key="kb_search_query")
    if st.button("Search", key="kb_search_button"):
        with st.spinner("Searching..."):
            response = requests.post(
                f"{BACKEND_URL}/api/v1/knowledge-base/search",
                json={"query": search_query},
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            if handle_response(response):
                results = response.json()
                if results:
                    for doc in results:
                        with st.expander(f"Result: {doc['name']}"):
                            st.write(f"Content: {doc['content'][:200]}...")
                            st.write(f"Metadata: {doc['meta_data']}")
                else:
                    st.info("No documents found matching your search query.")

def manage_documents():

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Document List")
    with col2:
        if st.button("Refresh", key="kb_refresh_documents"):
            st.session_state.documents = fetch_documents()

    if 'documents' not in st.session_state:
        st.session_state.documents = fetch_documents()

    if st.session_state.documents:
        df = pd.DataFrame(st.session_state.documents)
        df = df[['name', 'chunks']]  # Select only name and chunks columns
        
        # Display the dataframe
        st.dataframe(df, hide_index=True)
        
        # Add delete buttons below the table
        st.subheader("Delete Documents")
        for index, row in df.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(row['name'])
            with col2:
                if st.button(f"Delete", key=f"delete_{index}"):
                    if delete_document(row['name']):
                        st.success(f"Deleted document: {row['name']}")
                        st.session_state.documents = fetch_documents()
                        st.experimental_rerun()
    else:
        st.info("No documents found in the knowledge base.")

    # Clear Knowledge Base button
    if st.button("Clear Knowledge Base", key="clear_kb"):
        assistant_id = st.session_state.get("assistant_id")
        clear_knowledge_base(assistant_id)

def upload_file(uploaded_file):
    with st.spinner("Uploading file..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        response = requests.post(
            f"{BACKEND_URL}/api/v1/knowledge-base/upload-file",
            files=files,
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        handle_response(response, success_message="File uploaded successfully!")
        if response.status_code == 200:
            st.session_state.documents = fetch_documents()

def add_url(input_url):
    if input_url:
        with st.spinner("Processing URL..."):
            response = requests.post(
                f"{BACKEND_URL}/api/v1/knowledge-base/add-url",
                params={"url": input_url},
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            if handle_response(response, success_message=f"Successfully added URL: {input_url}"):
                if "processed_files" not in st.session_state:
                    st.session_state.processed_files = []
                st.session_state.processed_files.append(input_url)
                st.session_state.documents = fetch_documents()

def clear_knowledge_base(assistant_id):
    response = requests.post(
        f"{BACKEND_URL}/api/v1/knowledge-base/clear-knowledge-base",
        json={"assistant_id": assistant_id},
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    if response.status_code == 200:
        st.session_state["processed_files"] = []
        st.success("Knowledge base cleared")
        st.session_state.documents = []
    else:
        st.error(f"Failed to clear knowledge base: {response.text}")

def fetch_documents():
    response = requests.get(
        f"{BACKEND_URL}/api/v1/knowledge-base/documents",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    if handle_response(response):
        return response.json()
    return []

def delete_document(document_name):
    response = requests.delete(
        f"{BACKEND_URL}/api/v1/knowledge-base/documents/{document_name}",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    return handle_response(response)

def handle_response(response, success_message=None):
    if response.status_code == 200:
        if success_message:
            st.success(success_message)
        return True
    elif response.status_code == 400:
        error_detail = json.loads(response.text).get('detail', 'Unknown error')
        if isinstance(error_detail, list):
            for error in error_detail:
                st.error(f"Error: {error.get('msg', 'Unknown error')}")
        else:
            st.error(f"Error: {error_detail}")
    elif response.status_code == 401:
        st.error("Authentication failed. Please log in again.")
    elif response.status_code == 404:
        st.error("Resource not found. Please check your input.")
    else:
        st.error(f"An error occurred: {response.text}")
    return False

if __name__ == "__main__":
    knowledge_base_page()