import streamlit as st
import requests
from PIL import Image
from io import BytesIO
from utils.api import BACKEND_URL, get_auth_header

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_org_public_config(org_name):
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/organizations/public-config/{org_name}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        st.warning(f"HTTP error occurred while fetching organization config: {http_err}")
        if response.status_code == 404:
            st.info(f"Organization '{org_name}' not found. Please check the organization name.")
        return None
    except requests.exceptions.RequestException as req_err:
        st.warning(f"An error occurred while fetching organization config: {req_err}")
        return None
    except ValueError as json_err:
        st.warning(f"Invalid JSON in organization config response: {json_err}")
        st.info("Response content: " + response.text[:100] + "...")  # Show first 100 characters of response
        return None

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_main_image(org_name):
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/organizations/asset/{org_name}/login-form/main_image")
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except requests.exceptions.HTTPError as http_err:
        st.warning(f"HTTP error occurred while fetching main image: {http_err}")
        if response.status_code == 404:
            st.info(f"Main image for organization '{org_name}' not found.")
        return None
    except requests.exceptions.RequestException as req_err:
        st.warning(f"An error occurred while fetching main image: {req_err}")
        return None
    except IOError as io_err:
        st.warning(f"Error processing the image: {io_err}")
        return None

# Additional helper function for other assets
def get_organization_asset(org_id, asset_type):
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/organizations/asset/{org_id}/{asset_type}")
        response.raise_for_status()
        if asset_type in ["feature_flags", "roles"]:
            return response.json()
        else:
            return response.content
    except requests.exceptions.HTTPError as http_err:
        st.warning(f"HTTP error occurred while fetching {asset_type}: {http_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        st.warning(f"An error occurred while fetching {asset_type}: {req_err}")
        return None

@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_api_data(endpoint):
    """
    Fetch data from a specific API endpoint.
    
    Args:
    endpoint (str): The API endpoint to fetch data from

    Returns:
    dict: The fetched data
    """
    url = f"{BACKEND_URL}/api/v1/{endpoint}/"
    try:
        response = requests.get(url, headers=get_auth_header())
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch data from {endpoint}. Status code: {response.status_code}")
            return None
    except requests.RequestException as e:
        st.error(f"Failed to fetch data from {endpoint}: {str(e)}")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_batched_data():
    """
    Fetch batched data including analytics, organizations, and users.

    Returns:
    dict: The batched data containing analytics, organizations, and users
    """
    url = f"{BACKEND_URL}/api/v1/batched-data/"
    try:
        response = requests.get(url, headers=get_auth_header())
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch batched data. Status code: {response.status_code}")
            return None
    except requests.RequestException as e:
        st.error(f"Failed to fetch batched data: {str(e)}")
        return None

def send_chat_message(message, assistant_id):
    """
    Send a chat message to the API.
    
    Args:
    message (str): The message to send
    assistant_id (str): The ID of the assistant to send the message to

    Returns:
    requests.Response: The API response
    """
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/chat/",
            params={"message": message, "assistant_id": assistant_id},
            headers=get_auth_header(),
            stream=True
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred while sending the message: {str(e)}")
        return None

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_chat_history(assistant_id):
    """
    Fetch the chat history for a specific assistant.
    
    Args:
    assistant_id (str): The ID of the assistant

    Returns:
    list: The chat history
    """
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

def submit_feedback(user_id, query, response, is_upvote, usefulness_rating, feedback_text):
    """
    Submit feedback for a chat response.
    
    Args:
    user_id (str): The ID of the user submitting feedback
    query (str): The original query
    response (str): The response received
    is_upvote (bool): Whether the feedback is positive
    usefulness_rating (int): The usefulness rating (1-5)
    feedback_text (str): Additional feedback text

    Returns:
    bool: True if feedback was submitted successfully, False otherwise
    """
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
        if response.status_code == 200:
            return True
        else:
            st.error("Failed to submit feedback. Please try again.")
            return False
    except requests.RequestException as e:
        st.error(f"Failed to submit feedback: {str(e)}")
        return False

def update_user_role(user_id, new_role):
    """
    Update a user's role.
    
    Args:
    user_id (str): The ID of the user
    new_role (str): The new role to assign

    Returns:
    bool: True if the role was updated successfully, False otherwise
    """
    try:
        response = requests.put(
            f"{BACKEND_URL}/api/v1/users/{user_id}/role",
            json={"role": new_role},
            headers=get_auth_header()
        )
        if response.status_code == 200:
            return True
        else:
            st.error(f"Failed to update role. Status code: {response.status_code}")
            return False
    except requests.RequestException as e:
        st.error(f"Failed to update user role: {str(e)}")
        return False

def extend_user_trial(user_id, days):
    """
    Extend a user's trial period.
    
    Args:
    user_id (str): The ID of the user
    days (int): The number of days to extend the trial by

    Returns:
    bool: True if the trial was extended successfully, False otherwise
    """
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/users/{user_id}/extend-trial",
            json={"days": days},
            headers=get_auth_header()
        )
        if response.status_code == 200:
            return True
        else:
            st.error(f"Failed to extend trial. Status code: {response.status_code}")
            return False
    except requests.RequestException as e:
        st.error(f"Failed to extend user trial: {str(e)}")
        return False

def delete_user(user_id):
    """
    Delete a user.
    
    Args:
    user_id (str): The ID of the user to delete

    Returns:
    bool: True if the user was deleted successfully, False otherwise
    """
    try:
        response = requests.delete(
            f"{BACKEND_URL}/api/v1/users/{user_id}",
            headers=get_auth_header()
        )
        if response.status_code == 200:
            return True
        else:
            st.error(f"Failed to delete user. Status code: {response.status_code}")
            return False
    except requests.RequestException as e:
        st.error(f"Failed to delete user: {str(e)}")
        return False

def create_new_user(email, password, first_name, last_name, nickname, role, org):
    """
    Create a new user.
    
    Args:
    email (str): User's email
    password (str): User's password
    first_name (str): User's first name
    last_name (str): User's last name
    nickname (str): User's nickname
    role (str): User's role
    org (str): User's organization

    Returns:
    bool: True if the user was created successfully, False otherwise
    """
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/users",
            json={
                "email": email,
                "password": password,
                "first_name": first_name,
                "last_name": last_name,
                "nickname": nickname,
                "role": role,
                "organization": org
            },
            headers=get_auth_header()
        )
        if response.status_code == 200:
            return True
        else:
            st.error(f"Failed to create new user. Status code: {response.status_code}")
            return False
    except requests.RequestException as e:
        st.error(f"Failed to create new user: {str(e)}")
        return False