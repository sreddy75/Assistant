import streamlit as st
import requests
from config import BACKEND_URL

def knowledge_base_page():
    st.title("Knowledge Base Management")

    # Add document
    st.header("Add Document")
    doc_name = st.text_input("Document Name")
    doc_content = st.text_area("Document Content")
    if st.button("Add Document"):
        response = requests.post(
            f"{BACKEND_URL}/api/knowledge_base/documents",
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
        response = requests.get(
            f"{BACKEND_URL}/api/knowledge_base/search",
            params={"query": search_query},
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        if response.status_code == 200:
            results = response.json()
            for doc in results:
                st.write(f"Name: {doc['name']}")
                st.write(f"Content: {doc['content'][:100]}...")
                st.write("---")
        else:
            st.error("Failed to search documents")

    # List documents
    st.header("Your Documents")
    if st.button("Refresh Documents"):
        response = requests.get(
            f"{BACKEND_URL}/api/knowledge_base/documents",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        if response.status_code == 200:
            documents = response.json()
            for doc in documents:
                st.write(f"Name: {doc['name']}")
                if st.button(f"Delete {doc['name']}", key=f"delete_{doc['id']}"):
                    delete_response = requests.delete(
                        f"{BACKEND_URL}/api/knowledge_base/documents/{doc['id']}",
                        headers={"Authorization": f"Bearer {st.session_state.token}"}
                    )
                    if delete_response.status_code == 200:
                        st.success(f"Deleted document: {doc['name']}")
                    else:
                        st.error(f"Failed to delete document: {doc['name']}")
        else:
            st.error("Failed to fetch documents")

if __name__ == "__main__":
    knowledge_base_page()