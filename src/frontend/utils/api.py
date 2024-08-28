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
