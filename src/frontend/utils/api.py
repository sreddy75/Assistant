import os
import requests
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def fetch_data(endpoint):
    """
    Fetch data from the specified API endpoint.

    Args:
    endpoint (str): The API endpoint to fetch data from.

    Returns:
    dict or None: The JSON response from the API if successful, None otherwise.
    """
    try:
        response = requests.get(f"{BACKEND_URL}{endpoint}", headers=get_auth_header())
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Failed to fetch data from {endpoint}: {str(e)}")
        return None

def post_data(endpoint, data):
    """
    Post data to the specified API endpoint.

    Args:
    endpoint (str): The API endpoint to post data to.
    data (dict): The data to be posted.

    Returns:
    dict or None: The JSON response from the API if successful, None otherwise.
    """
    try:
        response = requests.post(f"{BACKEND_URL}{endpoint}", json=data, headers=get_auth_header())
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Failed to post data to {endpoint}: {str(e)}")
        return None

def put_data(endpoint, data):
    """
    Put data to the specified API endpoint.

    Args:
    endpoint (str): The API endpoint to put data to.
    data (dict): The data to be updated.

    Returns:
    dict or None: The JSON response from the API if successful, None otherwise.
    """
    try:
        response = requests.put(f"{BACKEND_URL}{endpoint}", json=data, headers=get_auth_header())
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Failed to update data at {endpoint}: {str(e)}")
        return None

def delete_data(endpoint):
    """
    Delete data at the specified API endpoint.

    Args:
    endpoint (str): The API endpoint to delete data from.

    Returns:
    bool: True if deletion was successful, False otherwise.
    """
    try:
        response = requests.delete(f"{BACKEND_URL}{endpoint}", headers=get_auth_header())
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        st.error(f"Failed to delete data at {endpoint}: {str(e)}")
        return False

def get_auth_header():
    """
    Get the authorization header for API requests.

    Returns:
    dict: The authorization header.
    """
    token = st.session_state.get('token')
    if not token:
        st.error("No authentication token found. Please log in.")
        return {}
    return {"Authorization": f"Bearer {token}"}

def fetch_organization_config(org_id):
    """
    Fetch the configuration for a specific organization.

    Args:
    org_id (str): The ID of the organization.

    Returns:
    dict or None: The organization configuration if successful, None otherwise.
    """
    return fetch_data(f"/api/v1/organizations/{org_id}/config")

def fetch_user_info(user_id):
    """
    Fetch information for a specific user.

    Args:
    user_id (str): The ID of the user.

    Returns:
    dict or None: The user information if successful, None otherwise.
    """
    return fetch_data(f"/api/v1/users/{user_id}")

def update_user_info(user_id, user_data):
    """
    Update information for a specific user.

    Args:
    user_id (str): The ID of the user.
    user_data (dict): The updated user data.

    Returns:
    dict or None: The updated user information if successful, None otherwise.
    """
    return put_data(f"/api/v1/users/{user_id}", user_data)

def fetch_all_analytics():
    return fetch_data("/api/v1/analytics/all-analytics")

def fetch_analytics_data(start_date, end_date):
    """
    Fetch analytics data for a specific date range.

    Args:
    start_date (str): The start date in ISO format (YYYY-MM-DD).
    end_date (str): The end date in ISO format (YYYY-MM-DD).

    Returns:
    dict or None: The analytics data if successful, None otherwise.
    """
    return fetch_data(f"/api/v1/analytics?start_date={start_date}&end_date={end_date}")

def send_chat_message(assistant_id, message):
    """
    Send a chat message to the specified assistant.

    Args:
    assistant_id (str): The ID of the assistant.
    message (str): The message to send.

    Returns:
    dict or None: The response from the assistant if successful, None otherwise.
    """
    return post_data(f"/api/v1/chat/", {"assistant_id": assistant_id, "message": message})

def upload_document(file):
    """
    Upload a document to the knowledge base.

    Args:
    file (file): The file to upload.

    Returns:
    dict or None: The response from the server if successful, None otherwise.
    """
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = requests.post(
            f"{BACKEND_URL}/api/v1/knowledge-base/upload-file",
            files=files,
            headers=get_auth_header()
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Failed to upload document: {str(e)}")
        return None

def search_knowledge_base(query):
    """
    Search the knowledge base with a query.

    Args:
    query (str): The search query.

    Returns:
    list or None: The search results if successful, None otherwise.
    """
    return post_data("/api/v1/knowledge-base/search", {"query": query})

def fetch_model_performance(model_id):
    """
    Fetch performance metrics for a specific model.

    Args:
    model_id (str): The ID of the model.

    Returns:
    dict or None: The model performance metrics if successful, None otherwise.
    """
    return fetch_data(f"/api/v1/models/{model_id}/performance")

def update_model_settings(model_id, settings):
    """
    Update settings for a specific model.

    Args:
    model_id (str): The ID of the model.
    settings (dict): The updated settings.

    Returns:
    dict or None: The updated model settings if successful, None otherwise.
    """
    return put_data(f"/api/v1/models/{model_id}/settings", settings)