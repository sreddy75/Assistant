import streamlit as st
import requests
import base64
from src.backend.kr8.utils.log import logger
from ui.components.utils import BACKEND_URL, determine_analyst

def manage_knowledge_base(assistant_id):
    if "loaded_dataframes" not in st.session_state:
        st.session_state["loaded_dataframes"] = {}
        
    if "processed_files" not in st.session_state:
        st.session_state["processed_files"] = []

    if "url_scrape_key" not in st.session_state:
        st.session_state["url_scrape_key"] = 0
    
    # Fetch documents from the knowledge base
    documents_response = requests.get(
        f"{BACKEND_URL}/api/v1/knowledge-base/documents",
        headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
    )
    if documents_response.status_code == 200:
        documents = documents_response.json()
    

    input_url = st.sidebar.text_input("Add URL to Knowledge Base", type="default", key=st.session_state["url_scrape_key"])
    add_url_button = st.sidebar.button("Add URL")
    if add_url_button:
        if input_url:
            with st.spinner("Processing URL..."):
                response = requests.post(
                    f"{BACKEND_URL}/api/v1/knowledge-base/add-url",
                    json={"url": input_url, "assistant_id": assistant_id},
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
                if response.status_code == 200:
                    st.success(f"Successfully processed and added URL: {input_url}")
                    st.session_state["processed_files"].append(input_url)
                    st.session_state["user_documents"] = documents
                else:
                    st.error(f"Failed to process URL: {response.text}")

    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 100
        
    uploaded_files = st.sidebar.file_uploader(
        "Upload Documents", type=["pdf", "docx", "txt", "csv", "xlsx", "xls"], key=st.session_state["file_uploader_key"], accept_multiple_files=True
    )

    if uploaded_files:
        for file in uploaded_files:
            with st.spinner(f"Processing {file.name}..."):
                try:
                    files = {"file": (file.name, file.getvalue(), file.type)}
                    data = {"assistant_id": assistant_id}
                    if file.name.endswith('.pdf'):
                        response = requests.post(f"{BACKEND_URL}/api/v1/knowledge-base/upload-pdf", files=files, data=data, headers={"Authorization": f"Bearer {st.session_state.token}"})
                    elif file.name.endswith('.docx') or file.name.endswith('.txt'):
                        response = requests.post(f"{BACKEND_URL}/api/v1/knowledge-base/upload-file", files=files, data=data, headers={"Authorization": f"Bearer {st.session_state.token}"})
                    elif file.name.endswith(('.csv', '.xlsx', '.xls')):
                        file_content = file.read()
                        analyst_type = determine_analyst(file, file_content)
                        data["analyst_type"] = analyst_type
                        if file.name.endswith('.csv'):
                            response = requests.post(f"{BACKEND_URL}/api/v1/knowledge-base/upload-csv", files=files, data=data, headers={"Authorization": f"Bearer {st.session_state.token}"})
                        else:
                            response = requests.post(f"{BACKEND_URL}/api/v1/knowledge-base/upload-excel", files=files, data=data, headers={"Authorization": f"Bearer {st.session_state.token}"})
                    else:
                        st.error(f"Unsupported file type: {file.name}")
                        continue

                    if response.status_code == 200:
                        st.success(f"Successfully processed {file.name}")
                        st.session_state["processed_files"].append(file.name)
                        if file.name.endswith(('.csv', '.xlsx', '.xls')):
                            st.session_state["loaded_dataframes"][response.json()] = {
                                "file_name": file.name,
                                "analyst_type": analyst_type
                            }
                        st.session_state["user_documents"] = get_user_documents(st.session_state.token)
                    else:
                        st.error(f"Error processing {file.name}: {response.text}")
                except Exception as e:
                    st.error(f"Error processing {file.name}: {str(e)}")
                    logger.error(f"Error processing {file.name}: {str(e)}")
                                        
        # Increment the file uploader key to force a refresh
        st.session_state["file_uploader_key"] += 1

    if st.session_state["processed_files"]:
        st.sidebar.markdown("### You are chatting with these files:")
        for file in st.session_state["processed_files"]:
            st.sidebar.write(file)

    if st.sidebar.button("Clear Knowledge Base"):
        response = requests.post(
            f"{BACKEND_URL}/api/v1/knowledge-base/clear-knowledge-base",
            json={"assistant_id": assistant_id},
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        if response.status_code == 200:
            st.session_state["processed_files"] = []
            st.sidebar.success("Knowledge base cleared")
            logger.info("Knowledge base cleared")
        else:
            st.sidebar.error(f"Failed to clear knowledge base: {response.text}")

    # # Fetch documents from the knowledge base
    # documents_response = requests.get(
    #     f"{BACKEND_URL}/api/v1/knowledge-base/documents",
    #     headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
    # )
    
    # documents = None
    # if documents_response.status_code == 200:
    #     documents = documents_response.json()


    # if documents is not None:
    #     st.subheader("Your Documents")
    #     for doc in documents:
    #         with st.expander(doc['name']):
    #             st.write(f"Type: {doc['meta_data'].get('type', 'Unknown')}")
    #             st.write(f"Created: {doc['created_at']}")
    #             st.write(f"Updated: {doc['updated_at']}")
    #             if st.button(f"Delete {doc['name']}", key=f"delete_{doc['name']}"):
    #                 response = requests.delete(
    #                     f"{BACKEND_URL}/api/v1/knowledge-base/documents/{doc['name']}",
    #                     json={"assistant_id": assistant_id},
    #                     headers={"Authorization": f"Bearer {st.session_state.token}"}
    #                 )
    #                 if response.status_code == 200:
    #                     st.success(f"Deleted {doc['name']}")
    #                     st.experimental_rerun()
    #                 else:
    #                     st.error(f"Failed to delete {doc['name']}: {response.text}")

    # # Search functionality
    # st.subheader("Search Documents")
    # search_query = st.text_input("Enter search query")
    # if search_query:
    #     search_results = requests.post(
    #         f"{BACKEND_URL}/api/v1/knowledge-base/search",
    #         json={"query": search_query, "assistant_id": assistant_id},
    #         headers={"Authorization": f"Bearer {st.session_state.token}"}
    #     )
    #     if search_results.status_code == 200:
    #         results = search_results.json()
    #         for result in results:
    #             st.write(f"Document: {result['name']}")
    #             st.write(f"Content: {result['content'][:200]}...")  # Show first 200 characters
    #             st.write("---")
    #     else:
    #         st.error(f"Failed to search documents: {search_results.text}")