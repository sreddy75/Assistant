import streamlit as st
import requests
import pandas as pd
from utils.api import BACKEND_URL
from utils.helpers import handle_response
from utils.file_processor import process_file
from utils.helpers import send_event

def render_knowledge_base():    
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
                    send_event("knowledge_base_file_uploaded", {"file_name": file.name, "file_size": file.size})
                st.success(f"Successfully uploaded {len(uploaded_files)} file(s)")

    with col2:
        st.subheader("Add URL")
        input_url = st.text_input("Enter URL", key="kb_url_input")
        if st.button("Add URL", key="kb_add_url_button"):
            add_url(input_url)
            send_event("knowledge_base_url_added", {"url": input_url})


    st.markdown('</div>', unsafe_allow_html=True)

def search_documents():
    st.markdown('<div class="search-section">', unsafe_allow_html=True)
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
        send_event("knowledge_base_cleared", {"assistant_id": assistant_id})
    st.markdown('</div>', unsafe_allow_html=True)

def upload_file(uploaded_file):
    with st.spinner(f"Uploading file: {uploaded_file.name}..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        response = requests.post(
            f"{BACKEND_URL}/api/v1/knowledge-base/upload-file",
            files=files,
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        handle_response(response, success_message=f"File {uploaded_file.name} uploaded successfully!")
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

if __name__ == "__main__":
    render_knowledge_base()