# src/frontend/utils/api_helpers.py
import logging
import json
from fastapi import logger
import streamlit as st
import requests
from typing import Iterator
from utils.api import BACKEND_URL, get_auth_header
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)


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
    logger.info(f"Sending chat message: message={message}, assistant_id={assistant_id}")
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/chat/",
            json={"message": message, "assistant_id": assistant_id},
            headers=get_auth_header(),
            stream=True
        )
        response.raise_for_status()
        logger.info("Chat message sent successfully")
        
        for chunk in response.iter_lines():
            if chunk:
                logger.debug(f"Received chunk: {chunk}")
                try:
                    json_response = json.loads(chunk)
                    if "response" in json_response:
                        yield json_response["response"]
                    elif "error" in json_response:
                        logger.error(f"Error in response: {json_response['error']}")
                        yield f"Error: {json_response['error']}"
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON, yielding raw chunk: {chunk.decode('utf-8')}")
                    yield chunk.decode('utf-8')
        
        logger.info("Chat response completed")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in chat message: {str(e)}", exc_info=True)
        yield f"An error occurred while sending the message: {str(e)}"

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
    
import time

def send_project_management_query(prompt: str, project_id: str, team_id: str) -> Iterator[str]:
    logger.info(f"Entering send_project_management_query function. prompt={prompt}, project_id={project_id}, team_id={team_id}")
    try:
        logger.info(f"Sending POST request to {BACKEND_URL}/api/v1/project-management/chat")
        response = requests.post(
            f"{BACKEND_URL}/api/v1/project-management/chat",
            json={"message": prompt, "project": project_id, "team": team_id},
            headers=get_auth_header(),
            stream=True
        )
        response.raise_for_status()
        logger.info("Project management query sent successfully")
        
        for line in response.iter_lines():
            if line:
                logger.debug(f"Raw response line: {line}")
                try:
                    json_response = json.loads(line)
                    if "response" in json_response:
                        yield json_response["response"]
                    elif "error" in json_response:
                        logger.error(f"Error in response: {json_response['error']}")
                        yield f"Error: {json_response['error']}"
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON, yielding raw line: {line.decode('utf-8')}")
                    yield line.decode('utf-8')
        
        logger.info("Response generator completed")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in project management query: {str(e)}", exc_info=True)
        yield f"An error occurred: {str(e)}"
        
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
        
def update_azure_devops_schema():
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/project-management/update-azure-devops-schema",
            headers=get_auth_header()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating Azure DevOps schema: {str(e)}")
        raise        