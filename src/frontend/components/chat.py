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


logger = logging.getLogger(__name__)

# Add this new function
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_org_public_config(org_name):
    response = requests.get(f"{BACKEND_URL}/api/v1/organizations/public-config/{org_name}")
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch organization config. Status code: {response.status_code}")
        return None
    
@st.cache_data(ttl=3600)  # Cache for 1 hour
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

        user_icon_response = requests.get(
            f"{BACKEND_URL}/api/v1/organizations/asset/{org_id}/chat_user_icon",
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if user_icon_response.status_code == 200:
            user_chat_icon = Image.open(BytesIO(user_icon_response.content))

    except Exception as e:
        logger.error(f"Error loading organization icons: {str(e)}")

    return system_chat_icon, user_chat_icon

@st.cache_data(ttl=100)  
def get_chat_history(assistant_id):
    chat_history_response = requests.get(
        f"{BACKEND_URL}/api/v1/chat/chat_history",
        params={"assistant_id": assistant_id},
        headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
    )
    if chat_history_response.status_code == 200:
        return chat_history_response.json()["history"]
    return []

def stream_response(response, response_area, pulsating_dot, response_placeholder):
    full_response = ""
    buffer = ""
    update_interval = 0.1  # Update every 0.1 seconds
    last_update = time.time()

    for chunk in response.iter_content(chunk_size=1):
        if chunk:
            buffer += chunk.decode('utf-8')
            current_time = time.time()
            
            if '\n' in buffer or (current_time - last_update) >= update_interval:
                lines = buffer.split('\n')
                for line in lines[:-1]:
                    try:
                        json_object = json.loads(line)
                        new_content = json_object.get('delta', '')
                        logger.debug(f"New content: {new_content}")

                        if new_content:
                            try:
                                delegated_response = json.loads(new_content)
                                if isinstance(delegated_response, dict) and "delegated_assistant" in delegated_response:
                                    new_content = f"Response from {delegated_response['delegated_assistant']}:\n{delegated_response['delegated_response']}\n"
                            except json.JSONDecodeError:
                                pass

                            full_response += new_content

                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON: {line}")
                
                buffer = lines[-1]
                
                if (current_time - last_update) >= update_interval:
                    with response_area:
                        pulsating_dot.empty()
                        response_placeholder.markdown(full_response, unsafe_allow_html=True)
                    last_update = current_time

    # Final update
    if full_response:
        with response_area:
            pulsating_dot.empty()
            response_placeholder.markdown(full_response, unsafe_allow_html=True)

    return full_response

# Add this new function
def send_chat_message(message, assistant_id):
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/chat/",
            params={"message": message, "assistant_id": assistant_id},
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        if response.status_code == 404:
            st.error("Chat endpoint not found. Please check the API configuration.")
        else:
            st.error(f"An error occurred while sending the message: {str(e)}")
        return None
    
def render_chat(user_id, user_role):
    system_chat_icon, user_chat_icon = load_org_icons()

    st.markdown("""
        <style>
        ... [Your existing CSS styles] ...
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

    if "messages" not in st.session_state:
        st.session_state["messages"] = get_chat_history(st.session_state["assistant_id"])

    if "feedback_submitted" not in st.session_state:
        st.session_state.feedback_submitted = {}
    
    if "feedback_timestamps" not in st.session_state:
        st.session_state.feedback_timestamps = {}
            
    if not st.session_state["messages"]:
        intro_response = requests.get(
            f"{BACKEND_URL}/api/v1/assistant/get-introduction/{st.session_state['assistant_id']}",
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if intro_response.status_code == 200:
            introduction = intro_response.json()["introduction"]
            if introduction:
                st.session_state["messages"].insert(0, {"role": "assistant", "content": introduction})

    for i, message in enumerate(st.session_state["messages"]):
        with st.chat_message(message["role"], avatar=system_chat_icon if message["role"] == "assistant" else user_chat_icon):
            content = message["content"]
            st.markdown(content, unsafe_allow_html=True)

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
                response = send_chat_message(user_input, st.session_state["assistant_id"])
                if response:
                    full_response = stream_response(response, response_area, pulsating_dot, response_placeholder)
                    st.session_state["messages"].append({"role": "assistant", "content": full_response})

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

            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")

        st.rerun()

    if st.button("Clear Conversation"):
        st.session_state["messages"] = []
        st.session_state.feedback_submitted = {}
        st.session_state.feedback_timestamps = {}
        st.rerun()
 
def render_project_management_chat(org_id, user_role):    
    try:
        projects = get_user_projects(org_id)
        if projects is None:
            st.warning("Azure DevOps is not configured for your organization. Please contact an administrator to set it up.")
            return
        if not projects:
            st.warning("No projects available. Please check your permissions or contact an administrator.")
            return
        
        # Create a container for the selection boxes
        selection_container = st.container()
        
        # Use columns to create a more compact layout
        with selection_container:
            col1, col2 = st.columns(2)
            
            with col1:
                project_names = [project['name'] for project in projects]
                selected_project_name = st.selectbox("Select Project", project_names, key="project_select")
                selected_project = next(project for project in projects if project['name'] == selected_project_name)
            
            with col2:
                teams = get_project_teams(org_id, selected_project['id'])
                if not teams:
                    st.warning("No teams available for the selected project. Please check your permissions or contact an administrator.")
                    return
                team_names = [team['name'] for team in teams]
                selected_team_name = st.selectbox("Select Team", team_names, key="team_select")
                selected_team = next(team for team in teams if team['name'] == selected_team_name)
        
        # Add a separator
        st.markdown("---")
        
    except requests.exceptions.RequestException as e:
        handle_project_management_error(e)
        return
    
    if "pm_messages" not in st.session_state:
        st.session_state.pm_messages = []

    # Create a container for chat messages
    chat_container = st.container()

    with chat_container:
        for message in st.session_state.pm_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Place the chat input below the chat messages
    if prompt := st.chat_input("Ask about your project"):
        st.session_state.pm_messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                try:
                    for response in send_project_management_query(prompt, selected_project['id'], selected_team['id']):
                        try:
                            response_json = json.loads(response)
                            if isinstance(response_json, dict) and "response" in response_json:
                                response_text = "".join(response_json["response"])
                            else:
                                response_text = response
                        except json.JSONDecodeError:
                            response_text = response
                        
                        full_response += response_text
                        message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                    st.session_state.pm_messages.append({"role": "assistant", "content": full_response})
                except Exception as e:
                    logger.error(f"Error in project management query: {str(e)}")
                    st.error("An error occurred while processing your query. Please try again later or contact an administrator.")

    # Place the clear conversation button at the bottom
    if st.button("Clear Conversation", key="clear_pm_chat"):
        st.session_state.pm_messages = []
        st.rerun()

def handle_project_management_error(e):
    if hasattr(e, 'response') and e.response is not None:
        if e.response.status_code == 404:
            st.warning("Azure DevOps is not configured for your organization. Please contact an administrator to set it up.")
        elif e.response.status_code == 422:
            st.error("Invalid input. Please check your project and team selection.")
            logger.error(f"Invalid input error: {str(e)}")
        else:
            logger.error(f"Error fetching projects or teams: {str(e)}")
            st.error(f"An error occurred while fetching projects and teams. Status code: {e.response.status_code}. Please try again later or contact an administrator.")
    else:
        logger.error(f"Error fetching projects or teams: {str(e)}")
        st.error("An unexpected error occurred. Please try again later or contact an administrator.")

                        
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