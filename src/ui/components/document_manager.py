import streamlit as st
import requests
from ui.components.utils import BACKEND_URL
from src.frontend.pages.knowledge_base import knowledge_base_page

def render_document_manager():
    
    # Fetch documents from the knowledge base
    documents_response = requests.get(
        f"{BACKEND_URL}/api/v1/knowledge-base/documents",
        headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
    )
    
    documents = None
    
    if documents_response.status_code == 200:
        documents = documents_response.json()

    # Display documents
    if documents:            
        for index, doc in enumerate(documents):
            chunks = doc.get('chunks', 1)
            chunk_info = f" ({chunks} chunks)" if chunks > 1 else ""
            
            with st.expander(f"{doc.get('name', 'Unnamed Document')}{chunk_info}"):
                st.write(f"Type: {doc.get('meta_data', {}).get('type', 'Unknown')}")
                st.write(f"Created: {doc.get('created_at', 'Unknown')}")
                st.write(f"Updated: {doc.get('updated_at', 'Unknown')}")
                
                # Create a unique key for each delete button
                delete_key = f"delete_{doc.get('id', '')}_{index}"
                if st.button(f"Delete {doc.get('name', 'Unnamed Document')}", key=delete_key):
                    delete_response = requests.delete(
                        f"{BACKEND_URL}/api/v1/knowledge-base/documents/{doc.get('name', '')}",
                        headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
                    )
                    if delete_response.status_code == 200:
                        st.success(f"Deleted {doc.get('name', 'Unnamed Document')}")
                        st.experimental_rerun()
                    else:
                        st.error(f"Failed to delete {doc.get('name', 'Unnamed Document')}: {delete_response.text}")

        
    knowledge_base_page()    