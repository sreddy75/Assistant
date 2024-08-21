import streamlit as st
import requests
from src.backend.core.config import settings

BACKEND_URL = settings.BACKEND_URL

def knowledge_base_page():

    # Add document
    st.header("Add Document")
    doc_name = st.text_input("Document Name")
    doc_content = st.text_area("Document Content")
    if st.button("Add Document"):
        response = requests.post(
            f"{BACKEND_URL}/api/v1/knowledge-base/documents",
            json={"name": doc_name, "content": doc_content},
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        if response.status_code == 200:
            st.success("Document added successfully!")
        else:
            st.error("Failed to add document")

    # Search documents
    st.header("Search Documents")
    search_query = st.text_input("Search Query")
    if st.button("Search"):
        response = requests.post(
            f"{BACKEND_URL}/api/v1/knowledge-base/search",
            json={"query": search_query},
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        if response.status_code == 200:
            results = response.json()
            if results:
                for doc in results:
                    st.subheader(doc['name'])
                    st.write(f"Content: {doc['content'][:200]}...")  # Display first 200 characters
                    st.write(f"Metadata: {doc['meta_data']}")
                    st.write("---")
            else:
                st.info("No documents found matching your search query.")
        else:
            st.error("Failed to search documents")

   # List documents
    st.header("Your Documents")
    if 'documents' not in st.session_state:
        st.session_state.documents = []

    def fetch_documents():
        response = requests.get(
            f"{BACKEND_URL}/api/v1/knowledge-base/documents",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        if response.status_code == 200:
            st.session_state.documents = response.json()
        else:
            st.error("Failed to fetch documents")

    if st.button("Refresh Documents"):
        fetch_documents()

    # Display documents and delete buttons
    for doc in st.session_state.documents:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"Name: {doc['name']}")
        with col2:
            if st.button(f"Delete {doc['name']}", key=f"delete_{doc['id']}"):
                delete_response = requests.delete(
                    f"{BACKEND_URL}/api/v1/knowledge-base/documents/{doc['name']}",
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
                if delete_response.status_code == 200:
                    st.success(f"Deleted document: {doc['name']}")
                    # Refresh the document list after successful deletion
                    fetch_documents()
                else:
                    st.error(f"Failed to delete document: {doc['name']}")
        st.write("---")

    # Fetch documents when the page loads
    if not st.session_state.documents:
        fetch_documents()

if __name__ == "__main__":
    knowledge_base_page()