from datetime import datetime, UTC
import os
import streamlit as st
import requests
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, DecodeError
from functools import wraps
from typing import Tuple
import re
from dotenv import load_dotenv
load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def login(email: str, password: str) -> bool:
    try:
        response = requests.post(f"{BACKEND_URL}/token", data={"username": email, "password": password})
        response.raise_for_status()
        
        if response.status_code == 200:
            token_data = response.json()
            token = token_data["access_token"]
            
            # Decode the token to check its expiry
            try:
                # Use 'HS256' as the algorithm, or whichever algorithm your backend uses
                decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256"])
                expiry = datetime.fromtimestamp(decoded_token['exp'], tz=UTC)
                if expiry <= datetime.now(UTC):
                    st.error("Your session has expired. Please log in again.")
                    return False
                
                st.session_state["token"] = token
                st.session_state["email"] = email
                st.session_state["user_id"] = token_data["user_id"]
                st.session_state["role"] = token_data["role"]
                st.session_state["nickname"] = token_data["nickname"]
                st.session_state.authenticated = True
                return True
            except ExpiredSignatureError:
                st.error("Your session has expired. Please log in again.")
                return False
            except (InvalidTokenError, DecodeError):
                st.error("Invalid token. Please log in again.")
                return False
        
        # If we get here, the login was unsuccessful
        st.error("Login failed. Please check your credentials.")
        return False
    
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return False
        
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return False

    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
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
        except (ExpiredSignatureError, InvalidTokenError, DecodeError):
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