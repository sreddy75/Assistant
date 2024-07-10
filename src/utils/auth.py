import streamlit as st
import requests
import jwt
from functools import wraps
from typing import Tuple
import re

BACKEND_URL = "http://localhost:8000"  # Change this to your FastAPI backend URL

def login(email, password):
    response = requests.post(f"{BACKEND_URL}/token", data={"username": email, "password": password})
    if response.status_code == 200:
        data = response.json()
        st.session_state['token'] = data['access_token']
        st.session_state['email'] = email
        return True
    elif response.status_code == 422:  # Validation error
        st.error("Login failed: Invalid input data")
    else:
        st.error(f"Login failed: {response.json().get('detail', 'Unknown error')}")
    return False

def register(email, password):
    response = requests.post(f"{BACKEND_URL}/register", json={"email": email, "password": password})
    if response.status_code == 200:
        return True, response.json()['message']
    return False, response.json()['detail']

def logout():
    for key in ['token', 'email']:
        if key in st.session_state:
            del st.session_state[key]

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
    elif response.status_code == 404:
        return False, "User not found. The reset link may have expired. Please request a new reset link."
    else:
        return False, response.json().get("detail", "Failed to reset password. Please try again.")

def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None