import codecs
import html
from io import BytesIO
import json
import os
import traceback
import requests
import streamlit as st
from typing import Optional
from ui.components.feedback_handler import submit_feedback, submit_simple_vote
from ui.components.utils import BACKEND_URL, sanitize_content, render_markdown
from src.backend.core.client_config import is_feedback_sentiment_analysis_enabled
from src.backend.kr8.utils.log import logger
from PIL import Image
from dotenv import load_dotenv
from transformers import GPT2Tokenizer
import time
from src.backend.core.client_config import get_client_name

# Load environment variables
load_dotenv()
BACKEND_URL=os.getenv("BACKEND_URL")

client_name = get_client_name()    

# Initialize the tokenizer
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

MAX_TOKENS = 4096  # Adjust based on the model 
BUFFER_TOKENS = 1000  # some room for the response
llm_os = None
def load_org_icons():
    client_name = get_client_name()
    org_id = st.session_state.get('org_id')
    
    if not org_id:
        logger.warning("Organization ID not found in session state")
        return None, None

    system_chat_icon = None
    user_chat_icon = None

    try:
        # Fetch chat system icon
        system_icon_response = requests.get(
            f"{BACKEND_URL}/api/v1/organizations/asset/{org_id}/chat_system_icon",
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if system_icon_response.status_code == 200:
            system_chat_icon = Image.open(BytesIO(system_icon_response.content))
        else:
            logger.error(f"Failed to load chat system icon. Status code: {system_icon_response.status_code}")

        # Fetch user icon
        user_icon_response = requests.get(
            f"{BACKEND_URL}/api/v1/organizations/asset/{org_id}/chat_user_icon",
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if user_icon_response.status_code == 200:
            user_chat_icon = Image.open(BytesIO(user_icon_response.content))
        else:
            logger.error(f"Failed to load user icon. Status code: {user_icon_response.status_code}")

    except Exception as e:
        logger.error(f"Error loading organization icons: {str(e)}")

    return system_chat_icon, user_chat_icon

# Load the custom icons
system_chat_icon, user_chat_icon = load_org_icons()

# New function to send events to the backend
def send_event(event_type, event_data, duration=None):
    try:
        user_id = st.session_state.get("user_id")        
        
        payload = {
            "user_id": user_id,            
            "event_type": event_type,
            "event_data": event_data,
            "duration": duration
        }
        response = requests.post(
            f"{BACKEND_URL}/api/v1/analytics/user-events",
            json=payload,
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if response.status_code != 200:
            logger.error(f"Failed to send event: {response.text}")
        else:
            logger.info(f"Event sent successfully: {event_type} for user {user_id}")
    except Exception as e:
        logger.error(f"Error sending event: {str(e)}")


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
    llm_os = None    
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
    
    # Fetch the assistant from the backend
    if "assistant_id" not in st.session_state:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/assistant/get-assistant",
            params={
                "user_id": st.session_state.get("user_id"),
                "org_id": st.session_state.get("org_id"),
                "user_role": st.session_state.get("role"),
                "user_nickname": st.session_state.get("nickname", "friend")
            },
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if response.status_code == 200:
            st.session_state["assistant_id"] = response.json()["assistant_id"]
        else:
            st.error("Failed to initialize assistant")
            return
                
    # Fetch assistant info
    assistant_info_response = requests.get(
        f"{BACKEND_URL}/api/v1/assistant/assistant-info/{st.session_state['assistant_id']}",
        headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
    )
    if assistant_info_response.status_code == 200:
        assistant_info = assistant_info_response.json()
        has_knowledge_base = assistant_info.get("has_knowledge_base", False)
    else:
        st.error("Failed to fetch assistant info")
        return    
    
    # Fetch chat history
    if "messages" not in st.session_state:
        chat_history_response = requests.get(
            f"{BACKEND_URL}/api/v1/chat/chat_history",
            params={"assistant_id": st.session_state["assistant_id"]},
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if chat_history_response.status_code == 200:
            st.session_state["messages"] = chat_history_response.json()["history"]
        else:
            st.session_state["messages"] = []

    # Fetch the introduction message only if the chat history is empty
    if not st.session_state["messages"]:
        intro_response = requests.get(
            f"{BACKEND_URL}/api/v1/assistant/get-introduction/{st.session_state['assistant_id']}",
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if intro_response.status_code == 200:
            introduction = intro_response.json()["introduction"]
            if introduction:
                st.session_state["messages"].insert(0, {"role": "assistant", "content": introduction})
        
    # Create LLM OS run
    if "llm_os_run_id" not in st.session_state:
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/v1/assistant/create-run",
                params={"assistant_id": st.session_state["assistant_id"]},
                headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
            )
            if response.status_code == 200:
                st.session_state["llm_os_run_id"] = response.json()["run_id"]
            else:
                raise Exception(response.text)
        except Exception as e:
            logger.error(f"Could not create LLM OS run: {str(e)}")
            st.warning("Could not create LLM OS run, is the database running?")
            return

    chat_container = st.container()
                
    with chat_container:
        for i, message in enumerate(st.session_state["messages"]):
            if message["role"] == "assistant":
                with st.chat_message(message["role"], avatar=system_chat_icon):
                    sanitized_content = sanitize_content(message["content"])
                    render_markdown(sanitized_content)
                    
                    query = st.session_state["messages"][i-1]["content"] if i > 0 else ""
                    
                    with st.expander("Please Provide feedback to help improve future answers", expanded=False):
                        if is_feedback_sentiment_analysis_enabled():
                            usefulness = st.slider("How useful was this response?", 1, 5, 3, key=f"usefulness_{i}")
                            feedback = st.text_area("Additional feedback (optional)", key=f"feedback_text_{i}")
                            if st.button("Submit Feedback", key=f"feedback_button_{i}"):
                                submit_feedback(user_id, query, sanitized_content, usefulness > 3, usefulness, feedback)
                                # Send event for feedback submission
                                send_event("feedback_submission", {"usefulness": usefulness, "feedback_length": len(feedback) if feedback else 0})
                        else:
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("👍", key=f"upvote_{i}"):
                                    submit_simple_vote(user_id, query, sanitized_content, True)
                                    # Send event for upvote
                                    send_event("vote_submission", {"is_upvote": True})
                            with col2:
                                if st.button("👎", key=f"downvote_{i}"):
                                    submit_simple_vote(user_id, query, sanitized_content, False)
                                    # Send event for downvote
                                    send_event("vote_submission", {"is_upvote": False})
                                
            elif message["role"] == "user":
                with st.chat_message(message["role"], avatar=user_chat_icon):
                    sanitized_content = sanitize_content(message["content"])
                    render_markdown(sanitized_content)

    if prompt := st.chat_input("What would you like to know?"):
        st.session_state["messages"].append({"role": "user", "content": prompt})
        
        start_time = time.time()
        
        # Send event for user message
        send_event("user_message", {"content_length": len(prompt)})

        with chat_container:
            with st.chat_message("user", avatar=user_chat_icon):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar=system_chat_icon):
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
                    
                    # Make API call to get assistant response
                    response = requests.post(
                        f"{BACKEND_URL}/api/v1/chat/",
                        params={
                            "message": context_prompt,
                            "assistant_id": st.session_state["assistant_id"]
                        },
                        headers={"Authorization": f"Bearer {st.session_state.get('token')}"},
                        stream=True
                    )

                    full_response = ""
                    buffer = b""
                    decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')

                    for chunk in response.iter_content(chunk_size=1):
                        if chunk:
                            buffer += chunk
                            try:
                                decoded_data = decoder.decode(buffer)
                                if '\n' in decoded_data:
                                    lines = decoded_data.split('\n')
                                    for line in lines[:-1]:
                                        try:
                                            json_object = json.loads(line)
                                            new_content = json_object.get('response', '')
                                            if new_content:
                                                full_response += new_content
                                                with response_area:
                                                    pulsating_dot.empty()
                                                    formatted_response = html.escape(full_response).replace('\n', '<br>').replace('**', '<strong>').replace('__', '<em>')
                                                    response_placeholder.markdown(f'<div style="white-space: pre-wrap;">{formatted_response}</div>', unsafe_allow_html=True)
                                        except json.JSONDecodeError:
                                            # If it's not a valid JSON, just append it to the response
                                            full_response += line
                                            with response_area:
                                                pulsating_dot.empty()
                                                formatted_response = html.escape(full_response).replace('\n', '<br>').replace('**', '<strong>').replace('__', '<em>')
                                                response_placeholder.markdown(f'<div style="white-space: pre-wrap;">{formatted_response}</div>', unsafe_allow_html=True)
                                    buffer = lines[-1].encode('utf-8')
                                else:
                                    buffer = decoded_data.encode('utf-8')
                            except UnicodeDecodeError:
                                # If we can't decode, just continue to the next chunk
                                continue

                    # Final update to ensure we display any remaining content
                    if buffer:
                        try:
                            decoded_data = decoder.decode(buffer, final=True)
                            json_object = json.loads(decoded_data)
                            new_content = json_object.get('response', '')
                            if new_content:
                                full_response += new_content
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            # If we can't decode or parse JSON, just append the raw decoded data
                            full_response += decoded_data

                    with response_area:
                        pulsating_dot.empty()
                        formatted_response = html.escape(full_response).replace('\n', '<br>').replace('**', '<strong>').replace('__', '<em>')
                        response_placeholder.markdown(f'<div style="white-space: pre-wrap;">{formatted_response}</div>', unsafe_allow_html=True)

                    sanitized_response = full_response  
                    st.session_state["messages"].append({"role": "assistant", "content": sanitized_response})
                    
                    # Send event for assistant response
                    response_time = time.time() - start_time
                    send_event("assistant_response", {"content_length": len(sanitized_response), "response_time": response_time}, duration=response_time)

                    with st.expander("Please Provide feedback to improve future answers", expanded=False):
                        if is_feedback_sentiment_analysis_enabled():
                            usefulness = st.slider("How useful was this response?", 1, 5, 3, key=f"usefulness_{len(st.session_state['messages'])-1}")
                            feedback = st.text_area("Additional feedback (optional)", key=f"feedback_text_{len(st.session_state['messages'])-1}")
                            if st.button("Submit Feedback", key=f"feedback_button_{len(st.session_state['messages'])-1}"):
                                submit_feedback(user_id, prompt, sanitized_response, usefulness > 3, usefulness, feedback)
                                # Send event for feedback submission
                                send_event("feedback_submission", {"usefulness": usefulness, "feedback_length": len(feedback) if feedback else 0})
                                st.success("Thank you for your feedback!")
                        else:
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("👍", key=f"upvote_{len(st.session_state['messages'])-1}"):
                                    submit_simple_vote(user_id, prompt, sanitized_response, True)
                                    # Send event for upvote
                                    send_event("vote_submission", {"is_upvote": True})
                                    st.success("Thank you for your positive feedback!")
                            with col2:
                                if st.button("👎", key=f"downvote_{len(st.session_state['messages'])-1}"):
                                    submit_simple_vote(user_id, prompt, sanitized_response, False)
                                    # Send event for downvote
                                    send_event("vote_submission", {"is_upvote": False})
                                    st.success("Thank you for your feedback. We'll work on improving!")

                except Exception as e:
                    with response_area:
                        pulsating_dot.empty()
                        st.error(f"An unexpected error occurred: {str(e)}")
                    logger.error(f"Unexpected error: {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    full_response = "I apologize, but I encountered an error while processing your request. Please try again."
                    response_placeholder.markdown(full_response)
                    # Send event for error
                    send_event("error", {"error_message": str(e)})

        response_time = time.time() - start_time
        logger.info(f"Response generated in {response_time:.2f} seconds")

    # Add a button to clear the conversation
    if st.button("Clear Conversation"):
        st.session_state["messages"] = []
        st.experimental_rerun()

if __name__ == "__main__":
    render_chat()