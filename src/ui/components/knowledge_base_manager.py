import streamlit as st
from kr8.document.reader.website import WebsiteReader
from kr8.utils.log import logger
import plotly.express as px
import plotly.graph_objects as go
from ui.components.file_processor import process_pdf, process_docx, process_txt, process_file_for_analyst
from ui.components.utils import get_user_documents, determine_analyst
import base64

def manage_knowledge_base(llm_os):
    
    # Ensure the table exists
    if llm_os.knowledge_base and llm_os.knowledge_base.vector_db:
        llm_os.knowledge_base.vector_db.create()
        
    if "loaded_dataframes" not in st.session_state:
        st.session_state["loaded_dataframes"] = {}
        
    if "processed_files" not in st.session_state:
        st.session_state["processed_files"] = []

    if "url_scrape_key" not in st.session_state:
        st.session_state["url_scrape_key"] = 0

    input_url = st.sidebar.text_input("Add URL to Knowledge Base", type="default", key=st.session_state["url_scrape_key"])
    add_url_button = st.sidebar.button("Add URL")
    if add_url_button:
        if input_url is not None:
            with st.spinner("Processing URLs..."):
                if f"{input_url}_scraped" not in st.session_state:
                    scraper = WebsiteReader(max_links=2, max_depth=1)
                    web_documents = scraper.read(input_url)
                    if web_documents:
                        llm_os.knowledge_base.load_documents(web_documents)
                        st.session_state[f"{input_url}_scraped"] = True
                        st.session_state["processed_files"].append(input_url)
                        st.session_state["user_documents"] = get_user_documents(llm_os.user_id)                        
                        logger.info(f"Successfully processed and added URL: {input_url}")
                    else:
                        st.sidebar.error("Could not read website")
                        logger.error(f"Could not read website: {input_url}")

    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 100
        
    uploaded_files = st.sidebar.file_uploader(
        "Upload Documents", type=["pdf", "json", "csv", "xlsx", "xls", "zip"], key=st.session_state["file_uploader_key"], accept_multiple_files=True
    )

    if uploaded_files:
        financial_analyst = next((assistant for assistant in llm_os.team if assistant.name == "Enhanced Financial Analyst"), None)
        data_analyst = next((assistant for assistant in llm_os.team if assistant.name == "Enhanced Data Analyst"), None)
        
        for file in uploaded_files:
            with st.spinner(f"Processing {file.name}..."):
                try:                    
                    if file.name.endswith('.pdf'):
                        success, message = process_pdf(file, llm_os)
                        if success:
                            st.success(message)
                            st.session_state["processed_files"].append(file.name)
                            st.session_state["user_documents"] = get_user_documents(llm_os.user_id)
                        else:
                            st.error(message)
                    elif file.name.endswith(('.csv', '.xlsx', '.xls')):
                        file_content = base64.b64encode(file.read()).decode('utf-8')
                        analyst_type = determine_analyst(file, file_content)
                        
                        if analyst_type == 'financial' and financial_analyst:
                            result = process_file_for_analyst(llm_os, file, file_content, financial_analyst)                            
                        elif data_analyst:
                            result = process_file_for_analyst(llm_os, file, file_content, data_analyst)
                        else:
                            result = "Error: No data analyst available to process this file"

                        if result.startswith("Error:"):
                            st.error(result)
                        else:
                            st.success(f"Loaded {file.name}: {result}")
                            st.session_state["loaded_dataframes"][result] = {
                                "file_name": file.name,
                                "analyst_type": analyst_type
                            }
                            st.session_state["processed_files"].append(file.name)
                            st.session_state["user_documents"] = get_user_documents(llm_os.user_id)
                except Exception as e:
                    st.error(f"Error processing {file.name}: {str(e)}")
                    logger.error(f"Error processing {file.name}: {str(e)}")
                                        
        # Increment the file uploader key to force a refresh
        st.session_state["file_uploader_key"] += 1

    if st.session_state["processed_files"]:
        st.sidebar.markdown("### You are chatting with these files:")
        for file in st.session_state["processed_files"]:
            st.sidebar.write(file)

    if llm_os.knowledge_base and llm_os.knowledge_base.vector_db:
        if st.sidebar.button("Clear Knowledge Base"):
            llm_os.knowledge_base.vector_db.clear()
            st.session_state["processed_files"] = []
            st.sidebar.success("Knowledge base cleared")
            logger.info("Knowledge base cleared")
    
    if llm_os.team and len(llm_os.team) > 0:
        for team_member in llm_os.team:
            if len(team_member.memory.chat_history) > 0:
                with st.expander(f"{team_member.name} Memory", expanded=False):
                    st.container().json(team_member.memory.get_llm_messages())    