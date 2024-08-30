import streamlit as st
import requests
import pandas as pd
from utils.api import BACKEND_URL, delete_data, fetch_data, post_data, search_knowledge_base, upload_document
from utils.helpers import handle_response
from utils.file_processor import process_file

def render_knowledge_base_page():    
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: var(--secondary-background-color);
        border-radius: 5px 5px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-color);
        color: white;
    }
    .upload-section, .search-section, .manage-section {
        background-color: var(--secondary-background-color);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Add Content", "Search Documents", "Manage Documents"])

    with tab1:
        add_content()

    with tab2:
        search_documents()

    with tab3:
        manage_documents()

def add_content():
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Upload Files")
        uploaded_files = st.file_uploader("Choose files", type=['txt', 'pdf', 'docx', 'csv', 'xlsx'], accept_multiple_files=True, key="kb_file_uploader")
        if uploaded_files:
            st.write("Selected files:")
            for file in uploaded_files:
                st.write(f"- {file.name}")
            if st.button("Upload Files", key="kb_upload_files_button"):
                for file in uploaded_files:
                    upload_file(file)
                st.success(f"Successfully uploaded {len(uploaded_files)} file(s)")

    with col2:
        st.subheader("Add URL")
        input_url = st.text_input("Enter URL", key="kb_url_input")
        if st.button("Add URL", key="kb_add_url_button"):
            add_url(input_url)

    st.markdown('</div>', unsafe_allow_html=True)

def search_documents():
    st.markdown('<div class="search-section">', unsafe_allow_html=True)
    search_query = st.text_input("Enter search query", key="kb_search_query")
    if st.button("Search", key="kb_search_button"):
        with st.spinner("Searching..."):
            results = search_knowledge_base(search_query)
            if results:
                for doc in results:
                    with st.expander(f"Result: {doc['name']}"):
                        st.write(f"Content: {doc['content'][:200]}...")
                        st.write(f"Metadata: {doc['meta_data']}")
            else:
                st.info("No documents found matching your search query.")
    st.markdown('</div>', unsafe_allow_html=True)

def manage_documents():
    st.markdown('<div class="manage-section">', unsafe_allow_html=True)
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
                        st.rerun()
    else:
        st.info("No documents found in the knowledge base.")

    # Clear Knowledge Base button
    if st.button("Clear Knowledge Base", key="clear_kb"):
        assistant_id = st.session_state.get("assistant_id")
        clear_knowledge_base(assistant_id)
    st.markdown('</div>', unsafe_allow_html=True)

def upload_file(uploaded_file):
    with st.spinner(f"Uploading file: {uploaded_file.name}..."):
        response = upload_document(uploaded_file)
        if response:
            st.success(f"File {uploaded_file.name} uploaded successfully!")
            st.session_state.documents = fetch_documents()
        else:
            st.error(f"Failed to upload file: {uploaded_file.name}")

def add_url(input_url):
    if input_url:
        with st.spinner("Processing URL..."):
            response = post_data("/api/v1/knowledge-base/add-url", {"url": input_url})
            if response:
                st.success(f"Successfully added URL: {input_url}")
                if "processed_files" not in st.session_state:
                    st.session_state.processed_files = []
                st.session_state.processed_files.append(input_url)
                st.session_state.documents = fetch_documents()
            else:
                st.error(f"Failed to add URL: {input_url}")

def clear_knowledge_base(assistant_id):
    response = post_data("/api/v1/knowledge-base/clear-knowledge-base", {"assistant_id": assistant_id})
    if response:
        st.session_state["processed_files"] = []
        st.success("Knowledge base cleared")
        st.session_state.documents = []
    else:
        st.error("Failed to clear knowledge base")

def fetch_documents():
    return fetch_data("/api/v1/knowledge-base/documents") or []

def delete_document(document_name):
    return delete_data(f"/api/v1/knowledge-base/documents/{document_name}")

if __name__ == "__main__":
    render_knowledge_base_page()