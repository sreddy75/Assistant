import sys
import json
import logging
import traceback
import streamlit as st
import requests
import time
from PIL import Image
from io import BytesIO
from utils.api import BACKEND_URL
from config.settings import get_client_name
from utils.api_helpers import get_project_teams, get_user_projects, send_chat_message, send_project_management_query

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

@st.cache_data(ttl=3600)
def get_org_public_config(org_name):
    response = requests.get(f"{BACKEND_URL}/api/v1/organizations/public-config/{org_name}")
    if response.status_code == 200:
        return response.json()
    st.error(f"Failed to fetch organization config. Status code: {response.status_code}")
    return None

@st.cache_data(ttl=3600)
def load_org_icons():
    org_id = st.session_state.get('org_id')
    if not org_id:
        st.warning("Organization ID not found in session state")
        return None, None

    system_chat_icon = user_chat_icon = None
    try:
        system_icon_response = requests.get(
            f"{BACKEND_URL}/api/v1/organizations/asset/{org_id}/chat_system_icon",
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if system_icon_response.status_code == 200:
            system_chat_icon = Image.open(BytesIO(system_icon_response.content))

        user_icon_response = requests.get(
            f"{BACKEND_URL}/api/v1/organizations/asset/{org_id}/chat_user_icon",
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if user_icon_response.status_code == 200:
            user_chat_icon = Image.open(BytesIO(user_icon_response.content))
    except Exception as e:
        logger.error(f"Error loading organization icons: {str(e)}")

    return system_chat_icon, user_chat_icon

def get_chat_history(chat_type):
    if chat_type == "general":
        if "general_messages" not in st.session_state:
            chat_history_response = requests.get(
                f"{BACKEND_URL}/api/v1/chat/chat_history",
                params={"assistant_id": st.session_state["assistant_id"]},
                headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
            )
            st.session_state["general_messages"] = chat_history_response.json()["history"] if chat_history_response.status_code == 200 else []
        return st.session_state["general_messages"]
    elif chat_type == "project_management":
        if "pm_messages" not in st.session_state:
            st.session_state["pm_messages"] = []
        return st.session_state["pm_messages"]
    else:
        raise ValueError(f"Unknown chat type: {chat_type}")

def clear_chat_history(chat_type):
    if chat_type == "general":
        st.session_state["general_messages"] = []
    elif chat_type == "project_management":
        st.session_state["pm_messages"] = []
    else:
        raise ValueError(f"Unknown chat type: {chat_type}")

    st.session_state.feedback_submitted = {}
    st.session_state.feedback_timestamps = {}
    st.rerun()

def send_message(message, chat_type, **kwargs):
    if chat_type == "general":
        return send_chat_message(message, st.session_state["assistant_id"])
    elif chat_type == "project_management":
        return send_project_management_query(message, kwargs['project_id'], kwargs['team_id'])
    else:
        raise ValueError(f"Unknown chat type: {chat_type}")

def stream_response(response, response_area, pulsating_dot, response_placeholder):
    full_response = ""
    buffer = ""
    chunk_size = 20  # Adjust this value to control the amount of text rendered at once
    delay = 0.05  # Adjust this value to control the speed of rendering

    try:
        for chunk in response:
            if chunk:
                try:
                    json_response = json.loads(chunk)
                    if "response" in json_response and "delta" in json_response:
                        # General chat format
                        new_content = json_response["delta"]
                    elif "response" in json_response:
                        # Project management format
                        new_content = json_response["response"][len(full_response):]
                    elif "error" in json_response:
                        raise Exception(json_response["error"])
                    else:
                        new_content = chunk
                except json.JSONDecodeError:
                    # If not JSON, treat the chunk as raw text
                    new_content = chunk

                buffer += new_content
                while len(buffer) >= chunk_size:
                    full_response += buffer[:chunk_size]
                    buffer = buffer[chunk_size:]
                    with response_area:
                        pulsating_dot.empty()
                        response_placeholder.markdown(full_response + "▌", unsafe_allow_html=True)
                    time.sleep(delay)

        # Display any remaining content in the buffer
        if buffer:
            full_response += buffer
            with response_area:
                pulsating_dot.empty()
                response_placeholder.markdown(full_response, unsafe_allow_html=True)

    except Exception as e:
        logger.error(f"Error in stream_response: {str(e)}")
        st.error(f"An error occurred while processing the response: {str(e)}")

    return full_response

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

def render_messages(messages, system_chat_icon, user_chat_icon):
    for i, message in enumerate(messages):
        with st.chat_message(message["role"], avatar=system_chat_icon if message["role"] == "assistant" else user_chat_icon):
            st.markdown(message["content"], unsafe_allow_html=True)

            if message["role"] == "assistant" and i > 0:
                render_feedback(i, messages[i-1]["content"], message["content"])

def render_feedback(index, query, response):
    feedback_key = f"feedback_{index}"
    current_time = time.time()
    
    if not st.session_state.feedback_submitted.get(feedback_key, False):
        with st.expander("Provide feedback", expanded=False):
            usefulness_rating = st.slider("Rate the usefulness of this response", 1, 5, 3, key=f"slider_{index}")
            feedback_text = st.text_area("Additional feedback (optional)", key=f"text_{index}")
            if st.button("Submit Feedback", key=f"button_{index}"):
                submit_feedback(st.session_state.get("user_id"), query, response, 
                                usefulness_rating > 3, usefulness_rating, feedback_text)
                st.session_state.feedback_submitted[feedback_key] = True
                st.session_state.feedback_timestamps[feedback_key] = current_time
                st.rerun()
    elif current_time - st.session_state.feedback_timestamps.get(feedback_key, 0) < 5:
        st.success("Feedback submitted successfully!")
    else:
        st.info("Thank you for your feedback!")

def render_chat_interface(send_message_func, message_key, system_chat_icon, user_chat_icon, chat_input_key):
    logger.info(f"Entering render_chat_interface function. message_key: {message_key}, chat_input_key: {chat_input_key}")
    chat_container = st.container()

    with chat_container:
        logger.info(f"Rendering {len(st.session_state[message_key])} messages")
        render_messages(st.session_state[message_key], system_chat_icon, user_chat_icon)

    if prompt := st.chat_input("What would you like to know?", key=chat_input_key):
        logger.info(f"Received chat input: {prompt}")
        st.session_state[message_key].append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user", avatar=user_chat_icon):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar=system_chat_icon):
                response_area = st.container()
                with response_area:
                    response_placeholder = st.empty()
                    pulsating_dot = st.empty()
                    
                    # Display pulsating dot while waiting for response
                    pulsating_dot.markdown(
                        """
                        <style>
                        .pulsating-dot {
                            width: 15px;
                            height: 15px;
                            background-color: #d92118;
                            border-radius: 50%;
                            animation: pulse 1s infinite;
                            display: inline-block;
                            margin-right: 5px;
                        }
                        @keyframes pulse {
                            0% { transform: scale(0.95); opacity: 0.7; }
                            50% { transform: scale(1.05); opacity: 1; }
                            100% { transform: scale(0.95); opacity: 0.7; }
                        }
                        </style>
                        <div class="pulsating-dot"></div> Thinking...
                        """,
                        unsafe_allow_html=True
                    )

                try:
                    logger.info(f"Calling send_message_func with prompt: {prompt}")
                    response = send_message_func(prompt)
                    logger.info(f"Received response object: {type(response)}")
                    full_response = stream_response(response, response_area, pulsating_dot, response_placeholder)
                    logger.info(f"Full response received: {full_response}")
                    st.session_state[message_key].append({"role": "assistant", "content": full_response})
                    render_feedback(len(st.session_state[message_key]) - 1, prompt, full_response)
                except Exception as e:
                    logger.error(f"Error in chat interface: {str(e)}", exc_info=True)
                    st.error(f"An error occurred while processing your request: {str(e)}")

        st.rerun()
    
    logger.info("Exiting render_chat_interface function")

def handle_chat_error(e, chat_type):
    if hasattr(e, 'response') and e.response is not None:
        status_code = e.response.status_code
        if status_code == 404:
            if chat_type == "project_management":
                st.warning("Azure DevOps is not configured for your organization. Please contact an administrator to set it up.")
            else:
                st.warning("The requested resource was not found. Please try again or contact an administrator.")
        elif status_code == 422:
            st.error("Invalid input. Please check your input and try again.")
        else:
            st.error(f"An error occurred while processing your request. Status code: {status_code}. Please try again later or contact an administrator.")
    else:
        st.error("An unexpected error occurred. Please try again later or contact an administrator.")
    logger.error(f"Error in {chat_type} chat: {str(e)}", exc_info=True)

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

    messages = get_chat_history("general")

    if "feedback_submitted" not in st.session_state:
        st.session_state.feedback_submitted = {}
    
    if "feedback_timestamps" not in st.session_state:
        st.session_state.feedback_timestamps = {}
            
    if not messages:
        intro_response = requests.get(
            f"{BACKEND_URL}/api/v1/assistant/get-introduction/{st.session_state['assistant_id']}",
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if intro_response.status_code == 200:
            introduction = intro_response.json()["introduction"]
            if introduction:
                messages.insert(0, {"role": "assistant", "content": introduction})

    def send_general_chat_message(message):
        return send_message(message, "general")

    render_chat_interface(
        send_general_chat_message,
        "general_messages",
        system_chat_icon,
        user_chat_icon,
        "general_chat_input"
    )

    if st.button("Clear Conversation", key="clear_general_chat"):
        clear_chat_history("general")

def render_project_management_chat(org_id, user_role):
    logger.info(f"Entering render_project_management_chat function. org_id: {org_id}, user_role: {user_role}")
    system_chat_icon, user_chat_icon = load_org_icons()

    try:
        projects = get_user_projects(org_id)
        if projects is None:
            logger.warning("Azure DevOps is not configured for the organization")
            st.warning("Azure DevOps is not configured for your organization. Please contact an administrator to set it up.")
            return
        if not projects:
            logger.warning("No projects available")
            st.warning("No projects available. Please check your permissions or contact an administrator.")
            return
        
        selection_container = st.container()
        
        with selection_container:
            col1, col2 = st.columns(2)
            
            with col1:
                project_names = [project['name'] for project in projects]
                selected_project_name = st.selectbox("Select Project", project_names, key="project_select")
                selected_project = next(project for project in projects if project['name'] == selected_project_name)
                logger.info(f"Selected project: {selected_project['name']}")
            
            with col2:
                teams = get_project_teams(org_id, selected_project['id'])
                logger.info(f"Fetched {len(teams)} teams for project {selected_project['name']}")
                if not teams:
                    logger.warning("No teams available for the selected project")
                    st.warning("No teams available for the selected project. Please check your permissions or contact an administrator.")
                    return
                team_names = [team['name'] for team in teams]
                selected_team_name = st.selectbox("Select Team", team_names, key="team_select")
                selected_team = next(team for team in teams if team['name'] == selected_team_name)
                logger.info(f"Selected team: {selected_team['name']}")
        
        st.markdown("---")
        logger.info("Rendered project and team selection")
        
        messages = get_chat_history("project_management")
        
        def send_pm_message(message):
            return send_message(message, "project_management", project_id=selected_project['id'], team_id=selected_team['id'])

        render_chat_interface(
            send_pm_message,
            "pm_messages",
            system_chat_icon,
            user_chat_icon,
            "pm_chat_input"
        )

        if st.button("Clear Conversation", key="clear_pm_chat"):
            clear_chat_history("project_management")

    except requests.exceptions.RequestException as e:
        handle_chat_error(e, "project_management")
    except Exception as e:
        logger.error(f"Unexpected error in project management chat: {str(e)}", exc_info=True)
        st.error("An unexpected error occurred. Please try again later or contact an administrator.")

    logger.info("Exiting render_project_management_chat function")