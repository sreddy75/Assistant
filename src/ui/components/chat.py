import time
import streamlit as st
import html
from kr8.utils.log import logger
from assistant import get_llm_os
from kr8.utils.ut import log_event
from kr8.document.reader.website import WebsiteReader
from kr8.document.reader.pdf import PDFReader

def sanitize_content(content):
    # Escape HTML entities to handle special characters
    return html.escape(content)

def render_chat():
    llm_id = st.session_state["llm_id"]
    llm_os = initialize_assistant(llm_id)

    try:
        st.session_state["llm_os_run_id"] = llm_os.create_run()
    except Exception:
        st.warning("Could not create LLM OS run, is the database running?")
        return

    assistant_chat_history = llm_os.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Ask me questions..."}]

    if prompt := st.chat_input():
        log_event("chat_input", prompt)
        st.session_state["messages"].append({"role": "user", "content": prompt})

    for message in st.session_state["messages"]:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            sanitized_content = sanitize_content(message["content"])
            st.markdown(sanitized_content)

    last_message = st.session_state["messages"][-1]
    if last_message.get("role") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            response = ""
            resp_container = st.empty()
            for delta in llm_os.run(question):
                response += delta
                sanitized_response = sanitize_content(response)
                resp_container.markdown(sanitized_response)
            st.session_state["messages"].append({"role": "assistant", "content": response})
            log_event("assistant_response", question, response=response)

    if llm_os.knowledge_base:
        manage_knowledge_base(llm_os)

def initialize_assistant(llm_id):
    if "llm_os" not in st.session_state or st.session_state["llm_os"] is None:
        logger.info(f"---*--- Creating {llm_id} LLM OS ---*---")
        llm_os = get_llm_os(
            llm_id=llm_id,
            ddg_search=st.session_state.get("ddg_search_enabled", True),
            file_tools=st.session_state.get("file_tools_enabled", False),
            research_assistant=st.session_state.get("research_assistant_enabled", True),
            investment_assistant=st.session_state.get("investment_assistant_enabled", True),            
            company_analyst=st.session_state.get("company_analyst_enabled", True),            
            maintenance_engineer=st.session_state.get("maintenance_engineer_enabled", True),            
        )
        st.session_state["llm_os"] = llm_os
    else:
        llm_os = st.session_state["llm_os"]
    return llm_os

def process_pdf(uploaded_file, llm_os):
    reader = PDFReader()
    auto_rag_documents = reader.read(uploaded_file)
    if not auto_rag_documents:
        return False, f"Could not read PDF: {uploaded_file.name}"
    
    total_docs = len(auto_rag_documents)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, doc in enumerate(auto_rag_documents):
        status_text.text(f"Processing document {i+1} of {total_docs}")
        llm_os.knowledge_base.load_document(doc, upsert=True)
        progress_bar.progress((i + 1) / total_docs)
        # time.sleep(0.1)  # To make the progress visible
    
    return True, f"Successfully processed {uploaded_file.name}"

def manage_knowledge_base(llm_os):
    if "processed_files" not in st.session_state:
        st.session_state["processed_files"] = []

    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 100

    uploaded_files = st.sidebar.file_uploader(
        "Add PDFs :page_facing_up:", type="pdf", key=st.session_state["file_uploader_key"], accept_multiple_files=True
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in st.session_state["processed_files"]:
                log_event("upload_pdf", uploaded_file.name)
                auto_rag_name = uploaded_file.name.split(".")[0]
                
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    success, message = process_pdf(uploaded_file, llm_os)
                    
                if success:
                    st.success(message)
                    st.session_state["processed_files"].append(uploaded_file.name)
                else:
                    st.error(message)
                    
                # Increment the file uploader key to force a refresh
                st.session_state["file_uploader_key"] += 1

    if st.session_state["processed_files"]:
        st.sidebar.markdown("### You are chatting with these files:")
        for file in st.session_state["processed_files"]:
            st.sidebar.write(file)

    if llm_os.knowledge_base and llm_os.knowledge_base.vector_db:
        if st.sidebar.button("Clear Knowledge Base"):
            log_event("clear_knowledge_base", "User cleared the knowledge base")
            llm_os.knowledge_base.vector_db.clear()
            st.session_state["processed_files"] = []
            st.sidebar.success("Knowledge base cleared")

    if llm_os.team and len(llm_os.team) > 0:
        for team_member in llm_os.team:
            if len(team_member.memory.chat_history) > 0:
                with st.expander(f"{team_member.name} Memory", expanded=False):
                    st.container().json(team_member.memory.get_llm_messages())