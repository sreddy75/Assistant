import streamlit as st
from kr8.document.reader.website import WebsiteReader
from kr8.utils.log import logger
import plotly.express as px
import plotly.graph_objects as go
from ui.components.file_processor import process_pdf, process_docx, process_txt, process_file_for_analyst
from ui.components.utils import get_user_documents, determine_analyst
import base64

def manage_knowledge_base(llm_os):
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
                        llm_os.knowledge_base.load_documents(web_documents, upsert=True)
                        st.session_state[f"{input_url}_scraped"] = True
                        st.session_state["processed_files"].append(input_url)
                        st.session_state["user_documents"] = get_user_documents(llm_os.user_id)                        
                        logger.info(f"Successfully processed and added URL: {input_url}")
                    else:
                        st.sidebar.error("Could not read website")
                        logger.error(f"Could not read website: {input_url}")

    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 100