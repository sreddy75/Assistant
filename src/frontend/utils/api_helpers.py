# src/frontend/utils/api_helpers.py
import logging
import json
from fastapi import logger
import streamlit as st
import requests
from typing import Any, Dict, Iterator, List
from utils.api import BACKEND_URL, get_auth_header
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)


def send_business_analysis_query(message: str, analysis_results: Dict[str, Any], org_id: int) -> Iterator[str]:
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/agile-team/business-analysis/chat",
            json={
                "query": message,
                "context": analysis_results,
                "org_id": org_id
            },
            headers=get_auth_header(),
            stream=True
        )
        response.raise_for_status()
        return handle_streaming_response(response)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in business analysis query: {str(e)}")
        yield f"An error occurred: {str(e)}"

def handle_streaming_response(response: requests.Response) -> Iterator[str]:
    for line in response.iter_lines():
        if line:
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
        
        for line in response.iter_lines():
            if line:
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
        
        logger.info("Chat response completed")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in chat message: {str(e)}", exc_info=True)
        yield f"An error occurred while sending the message: {str(e)}"

def query_knowledge_base(query: str) -> List[Dict[str, Any]]:
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/confluence/query",
            params={"query": query},
            headers=get_auth_header()
        )
        response.raise_for_status()
        return response.json()["results"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying knowledge base: {str(e)}")
        return []
    
def send_project_management_query(prompt: str, project_id: str, team_id: str, org_id: int) -> Iterator[str]:
    logger.info(f"Sending project management query: prompt={prompt}, project_id={project_id}, team_id={team_id}, org_id={org_id}")
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/project-management/chat",
            json={"message": prompt, "project": project_id, "team": team_id, "org_id": org_id},
            headers=get_auth_header(),
            stream=True
        )
        response.raise_for_status()
        logger.info("Project management query sent successfully")
        
        for line in response.iter_lines():
            if line:
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
        
        logger.info("Project management response completed")
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

def submit_feedback(feedback_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/feedback/submit-feedback",
            json=feedback_data,
            headers=get_auth_header()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise
        
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
    
def get_assistant_id(user_id, org_id, user_role, user_nickname):
    response = requests.get(
        f"{BACKEND_URL}/api/v1/assistant/get-assistant",
        params={
            "user_id": user_id,
            "org_id": org_id,
            "user_role": user_role,
            "user_nickname": user_nickname
        },
        headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
    )
    if response.status_code == 200:
        return response.json()["assistant_id"]
    else:
        raise Exception(f"Failed to get assistant ID. Status code: {response.status_code}")    
    
def get_confluence_spaces(org_id: int) -> List[Dict[str, Any]]:
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/agile-team/confluence/spaces",
            params={"org_id": org_id},
            headers=get_auth_header()
        )
        response.raise_for_status()
        return response.json()["spaces"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Confluence spaces: {str(e)}")
        return []

def sync_confluence_pages(org_id: int, space_key: str, page_ids: List[str]) -> Dict[str, Any]:
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/agile-team/confluence/sync",
            json={"space_key": space_key, "page_ids": page_ids},
            params={"org_id": org_id},
            headers=get_auth_header()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error syncing Confluence pages: {str(e)}")
        return {"success": False, "error": str(e)}
    
def sync_confluence_space(org_id: int, space_key: str) -> Dict[str, Any]:
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/agile-team/confluence/sync",
            json={"space_key": space_key, "page_ids": []},  # Add empty page_ids list
            params={"org_id": org_id},  # Move org_id to query parameters
            headers=get_auth_header()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error syncing Confluence space: {str(e)}")
        return {"success": False, "error": str(e)}

def get_confluence_pages(org_id: int, space_key: str) -> List[Dict[str, Any]]:
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/agile-team/confluence/pages/{space_key}",
            params={"org_id": org_id},
            headers=get_auth_header()
        )
        response.raise_for_status()
        return response.json()["pages"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Confluence pages: {str(e)}")
        return []

def generate_development_artifacts(org_id: int) -> Iterator[str]:
    logger.info(f"Generating development artifacts for org_id: {org_id}")
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/agile-team/confluence/generate_business_analysis",
            json={"org_id": org_id, "task": "Perform business analysis"},
            headers=get_auth_header(),
            stream=True
        )
        response.raise_for_status()
        logger.info("Development artifacts generation request sent successfully")
        
        for line in response.iter_lines():
            if line:
                logger.info(f"Received line from backend: {line}")
                try:
                    yield line.decode('utf-8')
                except UnicodeDecodeError:
                    logger.error(f"Failed to decode line: {line}")
            else:
                logger.warning("Received empty line from backend")
        
        logger.info("Finished processing backend response")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in generate_development_artifacts: {str(e)}", exc_info=True)
        yield json.dumps({"error": str(e)})
            
def send_business_analysis_query(message: str, context: Dict[str, Any], org_id: int) -> Iterator[str]:
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/agile-team/business-analysis/chat",
            json={
                "query": message,
                "context": context,
                "org_id": org_id
            },
            headers=get_auth_header(),
            stream=True
        )
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
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
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in business analysis query: {str(e)}")
        yield f"An error occurred: {str(e)}"