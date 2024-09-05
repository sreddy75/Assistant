import json
import logging
import traceback
import streamlit as st
import requests
import json
import time
from PIL import Image
from io import BytesIO
from utils.api import BACKEND_URL
from config.settings import get_client_name

logger = logging.getLogger(__name__)

def load_org_icons():
    client_name = get_client_name()
    org_id = st.session_state.get('org_id')

    if not org_id:
        st.warning("Organization ID not found in session state")
        return None, None

    system_chat_icon = None
    user_chat_icon = None

    try:
        system_icon_response = requests.get(
            f"{BACKEND_URL}/api/v1/organizations/asset/{org_id}/chat_system_icon",
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if system_icon_response.status_code == 200:
            system_chat_icon = Image.open(BytesIO(system_icon_response.content))
        else:
            st.error(f"Failed to load chat system icon. Status code: {system_icon_response.status_code}")

        user_icon_response = requests.get(
            f"{BACKEND_URL}/api/v1/organizations/asset/{org_id}/chat_user_icon",
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if user_icon_response.status_code == 200:
            user_chat_icon = Image.open(BytesIO(user_icon_response.content))
        else:
            st.error(f"Failed to load user icon. Status code: {user_icon_response.status_code}")

    except Exception as e:
        st.error(f"Error loading organization icons: {str(e)}")

    return system_chat_icon, user_chat_icon

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def stream_response(response, response_area, pulsating_dot, response_placeholder):
    full_response = ""
    buffer = ""

    for chunk in response.iter_content(chunk_size=1):
        if chunk:
            buffer += chunk.decode('utf-8')
            if '\n' in buffer:
                lines = buffer.split('\n')
                for line in lines[:-1]:
                    try:
                        json_object = json.loads(line)
                        new_content = json_object.get('delta', '')
                        logger.debug(f"New content: {new_content}")

                        if new_content:
                            # Check if it's a delegated response
                            try:
                                delegated_response = json.loads(new_content)
                                if isinstance(delegated_response, dict) and "delegated_assistant" in delegated_response:
                                    new_content = f"Response from {delegated_response['delegated_assistant']}:\n{delegated_response['delegated_response']}\n"
                            except json.JSONDecodeError:
                                pass  # Not a JSON response, use as is

                            full_response += new_content
                            logger.debug(f"Full response: {full_response}")

                            with response_area:
                                pulsating_dot.empty()
                                response_placeholder.markdown(full_response, unsafe_allow_html=True)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON: {line}")
                buffer = lines[-1]

    # Final update
    if full_response:
        with response_area:
            pulsating_dot.empty()
            response_placeholder.markdown(full_response, unsafe_allow_html=True)

    return full_response

def render_chat(user_id, user_role):
    system_chat_icon, user_chat_icon = load_org_icons()

    st.markdown("""
        <style>
        .stTabs {
            margin-bottom: -2rem;
        }
        .chat-container {
            display: flex;
            flex-direction: column;
            height: calc(100vh - 80px);
            margin-top: -2rem;
        }
        .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        white-space: pre-wrap;
        }
        .chat-message.user {
            background-color: #e6f3ff;
        }
        .chat-message.assistant {
            background-color: #f0f0f0;
        }
        .chat-message p {
            margin-bottom: 0.5rem;
        }
        .chat-message ul, .chat-message ol {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
            padding-left: 1.5rem;
        }
        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(255, 0, 0, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
        }
        .pulsating-dot {
            width: 20px;
            height: 20px;
            background: rgba(255, 0, 0, 1);
            border-radius: 50%;
            animation: pulse 2s infinite;
            display: inline-block;
            margin-right: 10px;
            vertical-align: middle;
        }
         .system-message {
            background-color: #f0f0f0;
            border-left: 5px solid #4CAF50;
            padding: 10px;
            margin-bottom: 10px;
            font-style: italic;
        }       
        .feedback-expander {
            margin-top: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
        } 
        </style>
        """, unsafe_allow_html=True)

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

    # Initialize feedback_submitted in session state
    if "feedback_submitted" not in st.session_state:
        st.session_state.feedback_submitted = {}
    
    if "feedback_timestamps" not in st.session_state:
        st.session_state.feedback_timestamps = {}
            
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

    # Display chat messages
    for i, message in enumerate(st.session_state["messages"]):
        with st.chat_message(message["role"], avatar=system_chat_icon if message["role"] == "assistant" else user_chat_icon):
            content = message["content"]
            st.markdown(content, unsafe_allow_html=True)

            # Add feedback expander for assistant messages (except the first one)
            if message["role"] == "assistant" and i > 0:
                feedback_key = f"feedback_{i}"
                current_time = time.time()
                
                if not st.session_state.feedback_submitted.get(feedback_key, False):
                    with st.expander("Provide feedback", expanded=False):
                        usefulness_rating = st.slider("Rate the usefulness of this response", 1, 5, 3, key=f"slider_{i}")
                        feedback_text = st.text_area("Additional feedback (optional)", key=f"text_{i}")
                        if st.button("Submit Feedback", key=f"button_{i}"):
                            submit_feedback(user_id, st.session_state["messages"][i-1]["content"], message["content"], 
                                            usefulness_rating > 3, usefulness_rating, feedback_text)
                            st.session_state.feedback_submitted[feedback_key] = True
                            st.session_state.feedback_timestamps[feedback_key] = current_time
                            st.rerun()
                elif current_time - st.session_state.feedback_timestamps.get(feedback_key, 0) < 5:
                    st.success("Feedback submitted successfully!")
                else:
                    st.info("Thank you for your feedback!")

    # Chat input
    if user_input := st.chat_input("What would you like to know?"):
        st.session_state["messages"].append({"role": "user", "content": user_input})

        with st.chat_message("user", avatar=user_chat_icon):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar=system_chat_icon):
            response_area = st.container()
            with response_area:
                response_placeholder = st.empty()
                pulsating_dot = st.empty()
                pulsating_dot.markdown('<div class="pulsating-dot"></div>', unsafe_allow_html=True)

            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/v1/chat/",
                    params={
                        "message": user_input,
                        "assistant_id": st.session_state["assistant_id"]
                    },
                    headers={"Authorization": f"Bearer {st.session_state.get('token')}"},
                    stream=True
                )
                response.raise_for_status()

                full_response = stream_response(response, response_area, pulsating_dot, response_placeholder)
                
                # The full_response is already properly formatted, so we don't need to check again
                st.session_state["messages"].append({"role": "assistant", "content": full_response})

                # Update the displayed message with the full response
                with response_area:
                    response_placeholder.markdown(full_response, unsafe_allow_html=True)

                # Add feedback expander for the new assistant message
                feedback_key = "feedback_new"
                current_time = time.time()
                
                if not st.session_state.feedback_submitted.get(feedback_key, False):
                    with st.expander("Provide feedback", expanded=False):
                        usefulness_rating = st.slider("Rate the usefulness of this response", 1, 5, 3, key="slider_new")
                        feedback_text = st.text_area("Additional feedback (optional)", key="text_new")
                        if st.button("Submit Feedback", key="button_new"):
                            submit_feedback(user_id, user_input, full_response, 
                                            usefulness_rating > 3, usefulness_rating, feedback_text)
                            st.session_state.feedback_submitted[feedback_key] = True
                            st.session_state.feedback_timestamps[feedback_key] = current_time
                            st.rerun()
                elif current_time - st.session_state.feedback_timestamps.get(feedback_key, 0) < 5:
                    st.success("Feedback submitted successfully!")
                else:
                    st.info("Thank you for your feedback!")

            except requests.RequestException as e:
                st.error(f"An error occurred while communicating with the server: {str(e)}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")

        st.rerun()

    # Add a button to clear the conversation
    if st.button("Clear Conversation"):
        st.session_state["messages"] = []
        st.session_state.feedback_submitted = {}
        st.session_state.feedback_timestamps = {}
        st.rerun()
                
def submit_feedback(user_id, query, response, is_upvote, usefulness_rating, feedback_text):
    response = requests.post(
        f"{BACKEND_URL}/api/v1/feedback/submit-feedback",
        json={
            "user_id": user_id,
            "query": query,
            "response": response,
            "is_upvote": is_upvote,
            "usefulness_rating": usefulness_rating,
            "feedback_text": feedback_text
        },
        headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
    )
    if response.status_code != 200:
        st.error("Failed to submit feedback. Please try again.")

def submit_simple_vote(user_id, query, response, is_upvote):
    response = requests.post(
        f"{BACKEND_URL}/api/v1/feedback/submit-vote",
        json={
            "user_id": user_id,
            "query": query,
            "response": response,
            "is_upvote": is_upvote
        },
        headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
    )
    if response.status_code != 200:
        st.error("Failed to submit vote. Please try again.")

if __name__ == "__main__":
    render_chat(None, None)