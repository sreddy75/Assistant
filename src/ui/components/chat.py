import random
import time
import httpx
import streamlit as st
import html
from kr8.utils.log import logger
from assistant import get_llm_os
from kr8.document.reader.website import WebsiteReader
from kr8.document.reader.pdf import PDFReader
from multiprocessing import Pool
import asyncio
from kr8.document import Document
from PIL import Image

# Load the custom icons
meerkat_icon = Image.open("images/meerkat_icon.png")
user_icon = Image.open("images/user_icon.png")
llm_os = None

def sanitize_content(content):
    return html.escape(content)

def render_chat():
    if "llm_id" not in st.session_state:
        st.session_state.llm_id = "gpt-4o"  # Set a default value
        logger.warning("llm_id not found in session state, using default value")

    llm_id = st.session_state.llm_id
    llm_os = initialize_assistant(llm_id)

    if llm_os is None:
        st.warning("The assistant is currently unavailable. Please try again later.")
        return
        
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

    # Create a container for chat messages
    chat_container = st.container()

    # Render chat messages
    with chat_container:
        for message in st.session_state["messages"]:
            if message["role"] == "system":
                continue
            elif message["role"] == "assistant":
                with st.chat_message(message["role"], avatar=meerkat_icon):
                    sanitized_content = sanitize_content(message["content"])
                    st.markdown(sanitized_content)
            elif message["role"] == "user":
                with st.chat_message(message["role"], avatar=user_icon):
                    sanitized_content = sanitize_content(message["content"])
                    st.markdown(sanitized_content)
            else:
                with st.chat_message(message["role"]):
                    sanitized_content = sanitize_content(message["content"])
                    st.markdown(sanitized_content)

    # Chat input at the bottom
    if prompt := st.chat_input("What would you like to know?"):
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user", avatar=user_icon):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar=meerkat_icon):
                response = ""
                resp_container = st.empty()
                try:
                    for delta in llm_os.run(prompt):
                        response += delta
                        sanitized_response = sanitize_content(response)
                        resp_container.markdown(sanitized_response)
                except httpx.ConnectError:
                    logger.error("Failed to connect to Ollama service. Working in offline mode.")
                    offline_response = "I'm sorry, but I'm currently offline. I can't process your request at the moment, but I'm here to chat about general topics that don't require real-time data or external connections. How else can I assist you? Simples!"
                    resp_container.markdown(offline_response)
                    response = offline_response
                st.session_state["messages"].append({"role": "assistant", "content": response})

    if llm_os.knowledge_base:
        manage_knowledge_base(llm_os)

def initialize_assistant(llm_id):
    if "llm_os" not in st.session_state or st.session_state["llm_os"] is None:
        logger.info(f"---*--- Creating {llm_id} LLM OS ---*---")
        try:
            llm_os = get_llm_os(
                llm_id=llm_id,  # Use the selected model
                web_search=st.session_state.get("web_search_enabled", True),
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
        except Exception as e:
            logger.error(f"Failed to initialize LLM OS: {e}")
            st.error(f"Failed to initialize the assistant. Error: {e}")
            return None
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
        logger.error(f"Could not read PDF: {uploaded_file.name}")
        return False, f"Could not read PDF: {uploaded_file.name}"
    
    logger.info(f"Successfully read PDF: {uploaded_file.name}. Found {len(auto_rag_documents)} documents.")
    
    total_chunks = 0
    chunks = []
    for doc in auto_rag_documents:
        doc_chunks = list(chunk_pdf(doc.content))
        chunks.extend(doc_chunks)
        total_chunks += len(doc_chunks)
    
    logger.info(f"Splitting {uploaded_file.name} into {total_chunks} chunks.")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    start_time = time.time()
    
    for i, chunk in enumerate(chunks):
        status_text.text(f"Processing chunk {i+1} of {total_chunks}")
        try:
            doc = Document(
                content=chunk, 
                name=f"{uploaded_file.name}_chunk_{i+1}", 
                meta_data={"source": uploaded_file.name, "chunk_number": i+1}
            )
            logger.info(f"Attempting to add document to knowledge base:")
            logger.info(f"  Name: {doc.name}")
            logger.info(f"  Metadata: {doc.meta_data}")
            logger.info(f"  Content preview: {doc.content[:100]}...")
            
            await asyncio.to_thread(llm_os.knowledge_base.load_documents, [doc], upsert=True)
            
            logger.info(f"Successfully added chunk {i+1} of {total_chunks} to knowledge base.")
        except Exception as e:
            logger.error(f"Error adding chunk {i+1} to knowledge base: {str(e)}")
        progress = (i + 1) / total_chunks
        progress_bar.progress(progress)
        
        # Estimate time remaining
        time_elapsed = time.time() - start_time
        time_per_chunk = time_elapsed / (i + 1)
        eta = time_per_chunk * (total_chunks - i - 1)
        status_text.text(f"Processing chunk {i+1} of {total_chunks}. ETA: {eta:.2f} seconds")
    
    logger.info(f"Finished processing {uploaded_file.name}. Total time: {time.time() - start_time:.2f} seconds.")
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

     # Add the debug button here
    debug_knowledge_base(llm_os)
    
    if llm_os.team and len(llm_os.team) > 0:
        for team_member in llm_os.team:
            if len(team_member.memory.chat_history) > 0:
                with st.expander(f"{team_member.name} Memory", expanded=False):
                    st.container().json(team_member.memory.get_llm_messages())
                    
                    
def debug_knowledge_base(llm_os):
    st.sidebar.markdown("### Knowledge Base Debug")
    if st.sidebar.button("Check Knowledge Base"):
        try:
            doc_count = llm_os.knowledge_base.vector_db.count_documents()
            st.sidebar.write(f"Documents in knowledge base: {doc_count}")
            logger.info(f"Documents in knowledge base: {doc_count}")
            
            if doc_count > 0:
                sample_query = "test query"
                results = llm_os.knowledge_base.search(sample_query)
                st.sidebar.write(f"Sample search results for '{sample_query}': {len(results)} documents")
                logger.info(f"Sample search results for '{sample_query}': {len(results)} documents")
                
                if results:
                    st.sidebar.write("First document preview:")
                    logger.info("First document preview:")
                    for i, doc in enumerate(results):
                        logger.info(f"Document {i+1}:")
                        for attr in ['name', 'meta_data', 'content', 'usage']:
                            if hasattr(doc, attr):
                                value = getattr(doc, attr)
                                if isinstance(value, str):
                                    logger.info(f"  {attr}: {value[:100]}...")
                                else:
                                    logger.info(f"  {attr}: {value}")
                        logger.info("---")
                    
                    # Display the content of the first document in the sidebar
                    if hasattr(results[0], 'content'):
                        st.sidebar.write(results[0].content[:100] + "...")
                    else:
                        st.sidebar.write("No 'content' attribute found in the document.")
                else:
                    st.sidebar.write("No documents found in search. Is like empty savannah - very strange!")
                    logger.info("No documents found in search.")
            else:
                st.sidebar.write("Knowledge base is empty. Is like meerkat burrow with no meerkats!")
                logger.info("Knowledge base is empty.")
                
        except Exception as e:
            st.sidebar.write(f"Error checking knowledge base: {str(e)}")
            logger.error(f"Knowledge base check failed: {str(e)}", exc_info=True)
            
def test_knowledge_base_search(llm_os):
    logger.info("Testing knowledge base search...")
    try:
        results = llm_os.knowledge_base.search("test query")
        logger.info(f"Search returned {len(results)} results")
        for i, doc in enumerate(results):
            logger.info(f"Result {i+1}:")
            logger.info(f"  Content length: {len(doc.content)}")
            logger.info(f"  Content preview: {doc.content[:200]}...")
            if hasattr(doc, 'meta_data'):
                logger.info(f"  Metadata: {doc.meta_data}")
            if hasattr(doc, 'name'):
                logger.info(f"  Name: {doc.name}")
            if hasattr(doc, 'similarity'):
                logger.info(f"  Similarity score: {doc.similarity}")
            logger.info("---")
    except Exception as e:
        logger.error(f"Error in knowledge base search: {str(e)}")
        
        
def inspect_random_documents(llm_os, num_docs=10):
    logger.info(f"Inspecting {num_docs} random documents from the knowledge base...")
    try:
        all_docs = llm_os.knowledge_base.vector_db.search("", limit=304)  # Get all documents
        if all_docs:
            sample_docs = random.sample(all_docs, min(num_docs, len(all_docs)))
            for i, doc in enumerate(sample_docs):
                logger.info(f"Random document {i+1} details:")
                logger.info(f"  Content length: {len(doc.content)}")
                logger.info(f"  Content preview: {doc.content[:200]}...")
                if hasattr(doc, 'meta_data'):
                    logger.info(f"  Metadata: {doc.meta_data}")
                if hasattr(doc, 'name'):
                    logger.info(f"  Name: {doc.name}")
                logger.info("---")
        else:
            logger.info("No documents found in the knowledge base.")
    except Exception as e:
        logger.error(f"Error inspecting random documents: {str(e)}")