import traceback
import streamlit as st
from typing import Optional
from ui.components.feedback_handler import submit_feedback, submit_simple_vote
from ui.components.utils import sanitize_content, render_markdown
from ui.components.assistant_initializer import initialize_assistant
from src.backend.core.client_config import is_feedback_sentiment_analysis_enabled
from kr8.utils.log import logger
from PIL import Image
from dotenv import load_dotenv
from transformers import GPT2Tokenizer
import time
from src.backend.core.client_config import get_client_name

# Load environment variables
load_dotenv()

client_name = get_client_name()    

# Initialize the tokenizer
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

MAX_TOKENS = 4096  # Adjust based on the model 
BUFFER_TOKENS = 1000  # some room for the response

# Load the custom icons
meerkat_icon = Image.open(f"src/backend/config/themes/{client_name}/chat_system_icon.png")
user_icon = Image.open(f"src/backend/config/themes/{client_name}/chat_user_icon.png")
llm_os = None


def count_tokens(text):
    return len(tokenizer.encode(text))

def truncate_conversation(messages, max_tokens):
    total_tokens = 0
    truncated_messages = []
    for message in reversed(messages):
        message_tokens = count_tokens(message['content'])
        if total_tokens + message_tokens > max_tokens:
            break
        total_tokens += message_tokens
        truncated_messages.insert(0, message)
    return truncated_messages

def render_chat(user_id: Optional[int] = None, user_role: Optional[str] = None):
    
    logger.info("Rendering chat interface...")

    st.markdown("""
        <style>
        .chat-message, .chat-message p, .chat-message li, .chat-message h1, .chat-message h2, .chat-message h3, .chat-message h4, .chat-message h5, .chat-message h6 {
            color: white !important;
        }
        .assistant-response, .assistant-response p, .assistant-response li, .assistant-response h1, .assistant-response h2, .assistant-response h3, .assistant-response h4, .assistant-response h5, .assistant-response h6 {
            color: white !important;
        }
        .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
    st.markdown("""
        <style>
        @keyframes pulse {
            0% { transform: scale(0.8); opacity: 0.7; }
            50% { transform: scale(1); opacity: 1; }
            100% { transform: scale(0.8); opacity: 0.7; }
        }
        .pulsating-dot {
            width: 20px; height: 20px;
            background-color: #ff0000;
            border-radius: 50%;
            display: inline-block;
            animation: pulse 1.5s ease-in-out infinite;
        }
        </style>
        """, unsafe_allow_html=True)

    
    if "llm_id" not in st.session_state:
        logger.warning("llm_id not found in session state, using default value")
        st.session_state.llm_id = "gpt-4o"

    llm_id = st.session_state.llm_id
    llm_os = initialize_assistant(llm_id, user_id)

    if llm_os is None:
        logger.error("Failed to initialize LLM OS")
        st.warning("The assistant is currently unavailable. Please try again later.")
        return
        
    try:
        st.session_state["llm_os_run_id"] = llm_os.create_run()
    except Exception as e:
        logger.error(f"Could not create LLM OS run: {str(e)}")
        st.warning("Could not create LLM OS run, is the database running?")
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

    chat_container = st.container()

    with chat_container:
        for i, message in enumerate(st.session_state["messages"]):
            if message["role"] == "assistant":
                with st.chat_message(message["role"], avatar=meerkat_icon):
                    sanitized_content = sanitize_content(message["content"])
                    render_markdown(sanitized_content)
                    
                    query = st.session_state["messages"][i-1]["content"] if i > 0 else ""
                    
                    with st.expander("Please Provide feedback to help improve future answers", expanded=False):
                        if is_feedback_sentiment_analysis_enabled():
                            usefulness = st.slider("How useful was this response?", 1, 5, 3, key=f"usefulness_{i}")
                            feedback = st.text_area("Additional feedback (optional)", key=f"feedback_text_{i}")
                            if st.button("Submit Feedback", key=f"feedback_button_{i}"):
                                submit_feedback(user_id, query, sanitized_content, usefulness > 3, usefulness, feedback)
                        else:
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("👍", key=f"upvote_{i}"):
                                    submit_simple_vote(user_id, query, sanitized_content, True)
                            with col2:
                                if st.button("👎", key=f"downvote_{i}"):
                                    submit_simple_vote(user_id, query, sanitized_content, False)
                                
            elif message["role"] == "user":
                with st.chat_message(message["role"], avatar=user_icon):
                    sanitized_content = sanitize_content(message["content"])
                    render_markdown(sanitized_content)

    if prompt := st.chat_input("What would you like to know?"):
        st.session_state["messages"].append({"role": "user", "content": prompt})
        
        start_time = time.time()
        
        with chat_container:
            with st.chat_message("user", avatar=user_icon):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar=meerkat_icon):
                response_area = st.container()
                
                with response_area:
                    pulsating_dot = st.empty()
                    pulsating_dot.markdown('<div class="pulsating-dot"></div>', unsafe_allow_html=True)
                    response_placeholder = st.empty()

                try:
                    current_project = st.session_state.get('current_project')
                    current_project_type = st.session_state.get('current_project_type')
                    context_prompt = f"In the context of the {current_project_type} project '{current_project}': {prompt}" if current_project and current_project_type else prompt                                        
                            
                    if llm_id.startswith("claude"):
                        current_messages = [{"role": "user", "content": prompt}]
                    else:
                        current_messages = st.session_state["messages"]
                    
                    full_response = ""
                    for chunk in llm_os.run(context_prompt, messages=current_messages, stream=True):
                        if isinstance(chunk, tuple):
                            chunk = chunk[0] if chunk else ""
                        elif not isinstance(chunk, str):
                            chunk = str(chunk)
                        full_response += chunk
                        with response_area:
                            pulsating_dot.markdown('<div class="pulsating-dot"></div>', unsafe_allow_html=True)
                            response_placeholder.markdown(sanitize_content(full_response) + "▌")
                        time.sleep(0.01)

                    sanitized_response = sanitize_content(full_response)
                    
                    with st.expander("Please Provide feedback to improve future answers", expanded=False):
                        if is_feedback_sentiment_analysis_enabled():
                            usefulness = st.slider("How useful was this response?", 1, 5, 3, key=f"usefulness_{len(st.session_state['messages'])-1}")
                            feedback = st.text_area("Additional feedback (optional)", key=f"feedback_text_{len(st.session_state['messages'])-1}")
                            if st.button("Submit Feedback", key=f"feedback_button_{len(st.session_state['messages'])-1}"):
                                submit_feedback(user_id, prompt, sanitized_response, usefulness > 3, usefulness, feedback)
                        else:
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("👍", key=f"upvote_{len(st.session_state['messages'])-1}"):
                                    submit_simple_vote(user_id, prompt, sanitized_response, True)
                            with col2:
                                if st.button("👎", key=f"downvote_{len(st.session_state['messages'])-1}"):
                                    submit_simple_vote(user_id, prompt, sanitized_response, False)

                except Exception as e:
                    with response_area:
                        pulsating_dot.empty()
                        st.error(f"An unexpected error occurred: {str(e)}")
                    logger.error(f"Unexpected error: {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    full_response = "I apologize, but I encountered an error while processing your request. Please try again."
                    response_placeholder.markdown(full_response)

        response_time = time.time() - start_time
        
    if llm_os.knowledge_base:
        from src.ui.components.knowledge_base_manager import manage_knowledge_base
        manage_knowledge_base(llm_os)