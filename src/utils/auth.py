from datetime import datetime, UTC, timedelta
import os
import streamlit as st
import requests
import jwt
from jwt.exceptions import InvalidTokenError, DecodeError
from functools import wraps
from typing import List, Tuple
import re
from dotenv import load_dotenv
load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def login(email: str, password: str) -> bool | str:
    response = requests.post(
        f"{BACKEND_URL}/token",
        data={"username": email, "password": password},
    )
    if response.status_code == 200:
        data = response.json()
        st.session_state["token"] = data["access_token"]
        st.session_state["user_id"] = data["user_id"]
        st.session_state["role"] = data["role"]
        st.session_state["nickname"] = data["nickname"]
        st.session_state["organization"] = data["organization"]
        return True
    elif response.status_code in [401, 403]:
        return response.json().get("detail", "An error occurred during login")
    return False

def get_user_id(email: str = None) -> int:
    """
    Get the user ID from the session state.
    If email is provided, it's used for logging purposes only.
    """
    user_id = st.session_state.get("user_id")
    if user_id is None:
        if email:
            st.error(f"User ID not found for email: {email}")
        else:
            st.error("User ID not found. Please log in again.")
        return None
    return user_id
    
def register(email, password, first_name, last_name, nickname, role):
    user_data = {
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "nickname": nickname,
        "role": role
    }
    response = requests.post(f"{BACKEND_URL}/register", json=user_data)
    if response.status_code == 200:
        return True, response.json()['message']
    return False, response.json().get('detail', 'Registration failed. Please try again.')

def logout():
    st.session_state.clear()

def is_authenticated():
    return 'token' in st.session_state and check_token_expiry()

def check_token_expiry():
    if "token" in st.session_state:
        token = st.session_state["token"]
        try:
            # Use 'HS256' as the algorithm, or whichever algorithm your backend uses
            decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256"])
            expiry = datetime.fromtimestamp(decoded_token['exp'], tz=UTC)
            if expiry <= datetime.now(UTC):
                st.warning("Your session has expired. Please log in again.")
                logout()
                return False
            return True
        except jwt.ExpiredSignatureError:
            st.warning("Your session has expired. Please log in again.")
            logout()
            return False
        except (InvalidTokenError, DecodeError):
            st.warning("Invalid token. Please log in again.")
            logout()
            return False
    return False

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_authenticated() or not check_token_expiry():
            st.warning("You need to login to access this page.")
            st.stop()
        return func(*args, **kwargs)
    return wrapper

def verify_token(token):
    try:
        jwt.decode(token, st.secrets['SECRET_KEY'], algorithms=['HS256'])
        return True
    except:
        return False

def verify_email(token: str) -> Tuple[bool, str]:
    response = requests.get(f"{BACKEND_URL}/verify-email/{token}")
    if response.status_code == 200:
        return True, "Email verified successfully"
    elif response.status_code == 400:
        return False, "Invalid or expired verification link. Please request a new one."
    elif response.status_code == 404:
        return False, "User not found. Please register again."
    else:
        return False, "An error occurred during verification. Please try again later."
        
def request_password_reset(email: str) -> Tuple[bool, str]:
    response = requests.post(f"{BACKEND_URL}/request-password-reset", json={"email": email})
    if response.status_code == 200:
        return True, "Password reset link sent to your email. Please check your inbox."
    else:
        return False, response.json().get("detail", "Failed to send reset link. Please try again.")
    
def reset_password(token: str, new_password: str) -> Tuple[bool, str]:
    response = requests.post(f"{BACKEND_URL}/reset-password", json={"token": token, "new_password": new_password})
    if response.status_code == 200:
        return True, "Password reset successfully"
    elif response.status_code == 400:
        return False, "Invalid or expired reset link. Please request a new one."
    elif response.status_code == 404:
        return False, "User not found. Please register again."
    else:
        return False, "An error occurred during password reset. Please try again later."
    
def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def get_all_users() -> List[dict]:
    """
    Fetch all users from the database via the backend API.
    
    Returns:
        A list of dictionaries containing user information.
    """
    try:
        response = requests.get(
            f"{BACKEND_URL}/users",
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            st.error("You don't have permission to view all users.")
            return []
        else:
            st.error(f"Failed to fetch users: {response.status_code} - {response.text}")
            return []
    except requests.RequestException as e:
        st.error(f"Error connecting to the server: {str(e)}")
        return []

def extend_user_trial(user_id: int, days: int = 7) -> bool:
    """
    Extend the trial period for a specific user.
    
    Args:
        user_id (int): The ID of the user whose trial is to be extended.
        days (int): The number of days to extend the trial by. Defaults to 7.
    
    Returns:
        bool: True if the trial was successfully extended, False otherwise.
    """
    try:
        new_trial_end_date = (datetime.now() + timedelta(days=days)).isoformat()
        response = requests.post(
            f"{BACKEND_URL}/extend-trial/{user_id}",
            json={"new_trial_end_date": new_trial_end_date},
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if response.status_code == 200:
            return True
        else:
            st.error(f"Failed to extend trial: {response.json().get('detail', 'Unknown error')}")
            return False
    except requests.RequestException as e:
        st.error(f"Error connecting to the server: {str(e)}")
        return False