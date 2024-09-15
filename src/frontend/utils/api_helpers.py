# src/frontend/utils/api_helpers.py

import streamlit as st
import requests
from typing import Iterator
from utils.api import BACKEND_URL, get_auth_header


def get_user_info(user_id: int) -> dict:
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/users/{user_id}",
            headers=get_auth_header()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch user info: {str(e)}")
        return {}
    
def send_chat_message(message: str, assistant_id: int) -> Iterator[str]:
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/chat/",
            json={"message": message, "assistant_id": assistant_id},
            headers=get_auth_header(),
            stream=True
        )
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                yield chunk.decode('utf-8')
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred while sending the message: {str(e)}")
        yield "I'm sorry, but I encountered an error while processing your query. Please try again later."

def get_user_projects(org_id):
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/project-management/projects",
            params={"org_id": org_id},
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None  # Indicate that Azure DevOps is not configured
        raise  # Re-raise other HTTP errors

def get_project_teams(org_id, project_id):
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/project-management/teams",
            params={"org_id": org_id, "project_id": project_id},
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return []  # Return an empty list if no teams are found
        raise 
    
def send_project_management_query(query, project, team):
    response = requests.post(
        f"{BACKEND_URL}/api/v1/project-management/chat",
        json={"query": query, "project": project, "team": team},
        headers={"Authorization": f"Bearer {st.session_state.get('token')}"},
        stream=True
    )
    response.raise_for_status()
    return response.iter_lines(decode_unicode=True)

def get_chat_history(assistant_id: int) -> list:
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/chat/chat_history",
            params={"assistant_id": assistant_id},
            headers=get_auth_header()
        )
        if response.status_code == 200:
            return response.json()["history"]
        else:
            st.error(f"Failed to fetch chat history. Status code: {response.status_code}")
            return []
    except requests.RequestException as e:
        st.error(f"Failed to fetch chat history: {str(e)}")
        return []

def submit_feedback(user_id: int, query: str, response: str, is_upvote: bool, usefulness_rating: int, feedback_text: str):
    try:
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
            headers=get_auth_header()
        )
        if response.status_code != 200:
            st.error("Failed to submit feedback. Please try again.")
    except requests.RequestException as e:
        st.error(f"Failed to submit feedback: {str(e)}")