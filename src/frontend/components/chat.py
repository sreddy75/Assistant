import random
import traceback
from venv import logger
import streamlit as st
import requests
import json
import time
import threading
from PIL import Image
from io import BytesIO
from src.backend.core.client_config import is_feedback_sentiment_analysis_enabled
from utils.helpers import sanitize_content, render_markdown, send_event
from utils.api import BACKEND_URL
from utils.auth import is_authenticated
from utils.file_processor import process_file_for_analyst
from config.settings import get_client_name

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
                        new_content = json_object.get('response', '')

                        if new_content:
                            full_response = new_content  # Always use the full new_content

                            with response_area:
                                if full_response.strip():
                                    pulsating_dot.empty()
                                    response_placeholder.markdown(full_response, unsafe_allow_html=True)
                    except json.JSONDecodeError:
                        print(f"Failed to parse JSON: {line}")  # For debugging
                buffer = lines[-1]

    # Final update
    if full_response:
        with response_area:
            pulsating_dot.empty()
            try:
                rendered_response = render_markdown(full_response)
                if rendered_response is None:
                    rendered_response = full_response  # Fall back to unrendered response

                if rendered_response.strip():
                    response_placeholder.markdown(rendered_response, unsafe_allow_html=True)
                else:
                    response_placeholder.markdown("No response received.", unsafe_allow_html=True)
            except Exception as e:
                print(f"Error in rendering response: {str(e)}")
                response_placeholder.markdown("An error occurred while rendering the response.", unsafe_allow_html=True)

    return full_response

def render_chat(user_id, user_role):
    system_chat_icon, user_chat_icon = load_org_icons()

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
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"], avatar=system_chat_icon if message["role"] == "assistant" else user_chat_icon):
            st.markdown(render_markdown(sanitize_content(message["content"])), unsafe_allow_html=True)

    # Chat input
    if user_input := st.chat_input("What would you like to know?"):
        st.session_state["messages"].append({"role": "user", "content": user_input})
        
        with st.chat_message("user", avatar=user_chat_icon):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar=system_chat_icon):
            response_placeholder = st.empty()
            full_response = ""

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

                for chunk in response.iter_content(chunk_size=1):
                    if chunk:
                        full_response += chunk.decode('utf-8')
                        response_placeholder.markdown(render_markdown(sanitize_content(full_response)), unsafe_allow_html=True)

                st.session_state["messages"].append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")
                logger.error(f"Unexpected error: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")

        st.rerun()

    # Add a button to clear the conversation
    if st.button("Clear Conversation"):
        st.session_state["messages"] = []
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