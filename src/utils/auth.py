import os
import streamlit as st
import requests
import jwt
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
            token = response.json().get("access_token")
            user_id = response.json().get("user_id")
            if token:
                st.session_state["token"] = token
                st.session_state["email"] = email
                st.session_state["user_id"] = user_id 
                st.session_state.authenticated = True
                return True
                    
        # If we get here, the login was unsuccessful
        error_message = "Unknown error"
        try:
            error_message = response.json().get("detail", error_message)
        except requests.exceptions.JSONDecodeError:
            # If JSON decoding fails, use the raw text of the response
            error_message = response.text or error_message
        
        st.error(f"Login failed: {error_message}")
        return False
    
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return False
    
def register(email, password):
    response = requests.post(f"{BACKEND_URL}/register", json={"email": email, "password": password})
    if response.status_code == 200:
        return True, response.json()['message']
    return False, response.json()['detail']

def logout():
    st.session_state.clear()

def is_authenticated():
    return 'token' in st.session_state

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
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