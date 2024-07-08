import time
import streamlit as st
import html
from kr8.utils.log import logger
from assistant import get_llm_os
# from kr8.utils.ut import log_event
from kr8.document.reader.website import WebsiteReader
from kr8.document.reader.pdf import PDFReader
from multiprocessing import Pool
import asyncio
from kr8.document import Document

def sanitize_content(content):
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
        # log_event("chat_input", prompt)
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
            # log_event("assistant_response", question, response=response)

    if llm_os.knowledge_base:
        manage_knowledge_base(llm_os)

def initialize_assistant(llm_id):
    if "llm_os" not in st.session_state or st.session_state["llm_os"] is None:
        logger.info(f"---*--- Creating {llm_id} LLM OS ---*---")
        llm_os = get_llm_os(
            llm_id=llm_id,
            ddg_search=st.session_state.get("ddg_search_enabled", True),
            file_tools=st.session_state.get("file_tools_enabled", True),
            research_assistant=st.session_state.get("research_assistant_enabled", False),
            investment_assistant=st.session_state.get("investment_assistant_enabled", False),            
            company_analyst=st.session_state.get("company_analyst_enabled", False),            
            maintenance_engineer=st.session_state.get("maintenance_engineer_enabled", False),            
            product_owner=st.session_state.get("product_owner_enabled", True),
            business_analyst=st.session_state.get("business_analyst_enabled", True),
            quality_analyst=st.session_state.get("quality_analyst_enabled", True),
        )
        st.session_state["llm_os"] = llm_os
    else:
        llm_os = st.session_state["llm_os"]
    return llm_os

def chunk_pdf(pdf_content, chunk_size=1000):
    words = pdf_content.split()
    for i in range(0, len(words), chunk_size):
        yield ' '.join(words[i:i+chunk_size])

async def process_pdf_async(uploaded_file, llm_os):
    reader = PDFReader()
    auto_rag_documents = reader.read(uploaded_file)
    if not auto_rag_documents:
        return False, f"Could not read PDF: {uploaded_file.name}"
    
    total_chunks = 0
    chunks = []
    for doc in auto_rag_documents:
        doc_chunks = list(chunk_pdf(doc.content))
        chunks.extend(doc_chunks)
        total_chunks += len(doc_chunks)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    start_time = time.time()  # Define start_time here
    
    for i, chunk in enumerate(chunks):
        status_text.text(f"Processing chunk {i+1} of {total_chunks}")
        await asyncio.to_thread(llm_os.knowledge_base.load_documents, [Document(content=chunk)], upsert=True)
        progress = (i + 1) / total_chunks
        progress_bar.progress(progress)
        
        # Estimate time remaining
        time_elapsed = time.time() - start_time
        time_per_chunk = time_elapsed / (i + 1)
        eta = time_per_chunk * (total_chunks - i - 1)
        status_text.text(f"Processing chunk {i+1} of {total_chunks}. ETA: {eta:.2f} seconds")
    
    return True, f"Successfully processed {uploaded_file.name}"


def process_pdfs_parallel(uploaded_files, llm_os):
    with Pool() as pool:
        results = pool.starmap(PDFReader().read, [(file,) for file in uploaded_files])
    all_documents = [doc for result in results for doc in result]
    llm_os.knowledge_base.load_documents(all_documents, upsert=True)
    return True, f"Successfully processed {len(uploaded_files)} files"

def manage_knowledge_base(llm_os):
    if "processed_files" not in st.session_state:
        st.session_state["processed_files"] = []

    if "url_scrape_key" not in st.session_state:
        st.session_state["url_scrape_key"] = 0

    input_url = st.sidebar.text_input("Add URL to Knowledge Base", type="default", key=st.session_state["url_scrape_key"])
    add_url_button = st.sidebar.button("Add URL")
    if add_url_button:
        # log_event("add_url", input_url)
        if input_url is not None:
            with st.spinner("Processing URLs..."):
                if f"{input_url}_scraped" not in st.session_state:
                    scraper = WebsiteReader(max_links=2, max_depth=1)
                    web_documents = scraper.read(input_url)
                    if web_documents:
                        llm_os.knowledge_base.load_documents(web_documents, upsert=True)
                        st.session_state[f"{input_url}_scraped"] = True
                        st.session_state["processed_files"].append(input_url)
                        st.sidebar.success(f"Successfully processed and added: {input_url}")
                    else:
                        st.sidebar.error("Could not read website")

    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 100

    uploaded_files = st.sidebar.file_uploader(
        "Add PDFs :page_facing_up:", type="pdf", key=st.session_state["file_uploader_key"], accept_multiple_files=True
    )
    
    if uploaded_files:
        # log_event("upload_pdfs", [file.name for file in uploaded_files])
        
        for uploaded_file in uploaded_files:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                success, message = asyncio.run(process_pdf_async(uploaded_file, llm_os))
            
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
            # log_event("clear_knowledge_base", "User cleared the knowledge base")
            llm_os.knowledge_base.vector_db.clear()
            st.session_state["processed_files"] = []
            st.sidebar.success("Knowledge base cleared")

    if llm_os.team and len(llm_os.team) > 0:
        for team_member in llm_os.team:
            if len(team_member.memory.chat_history) > 0:
                with st.expander(f"{team_member.name} Memory", expanded=False):
                    st.container().json(team_member.memory.get_llm_messages())