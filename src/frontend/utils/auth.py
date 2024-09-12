import json
import time
import streamlit as st
import requests
from PIL import Image
from io import BytesIO

import toml
from utils.api import BACKEND_URL, get_auth_header
from utils.helpers import get_client_name, validate_email, validate_password

client_name = get_client_name()

def get_org_public_config(org_name):
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/organizations/public-config/{org_name}")
        if response.status_code == 200:
            content = response.text
            try:
                # First, try to parse as JSON
                return json.loads(content)
            except json.JSONDecodeError:
                try:
                    # If JSON parsing fails, try to parse as TOML
                    return toml.loads(content)
                except toml.TomlDecodeError:
                    st.warning(f"Failed to parse configuration file. Neither JSON nor TOML format.")
                    return None
        else:
            st.warning(f"Failed to fetch organization config. Status code: {response.status_code}")
            return None
    except requests.RequestException as e:
        st.warning(f"Failed to fetch organization config: {str(e)}")
        return None
    
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_main_image(org_name):
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/organizations/asset/{org_name}/login-form/main_image")
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
        else:
            st.warning(f"Failed to load organization image. Status code: {response.status_code}")
            return None
    except requests.RequestException as e:
        st.warning(f"Failed to fetch organization image: {str(e)}")
        return None
    except IOError as e:
        st.warning(f"Failed to process organization image: {str(e)}")
        return None

def register_form(org_config):
    new_email = st.text_input("Email", key="register_email")
    new_password = st.text_input("Password", type="password", key="register_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
    first_name = st.text_input("First Name", key="register_first_name")
    last_name = st.text_input("Last Name", key="register_last_name")
    nickname = st.text_input("Nickname", key="register_nickname")

    if org_config and 'roles' in org_config:
        role = st.selectbox("Role", options=org_config['roles'], key="register_role")
    else:
        role = st.text_input("Role", key="register_role")
        st.info("Roles could not be fetched. Please enter your role manually.")

    if st.button("Register"):
        if validate_email(new_email) and validate_password(new_password):
            if new_password == confirm_password:
                register(new_email, new_password, first_name, last_name, nickname, role)
            else:
                st.error("Passwords do not match.")
        else:
            st.error("Please enter a valid email and a strong password.")

def register(email, password, first_name, last_name, nickname, role):
    response = requests.post(
        f"{BACKEND_URL}/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "nickname": nickname,
            "role": role
        },
        params={"org_name": client_name}
    )
    if response.status_code == 200:
        st.success("Registration successful! Please check your email for verification.")
    else:
        st.error(response.json().get("detail", "Registration failed"))

def reset_password_form():
    reset_email = st.text_input("Email", key="reset_email")
    if st.button("Reset Password"):
        if validate_email(reset_email):
            reset_password(reset_email)
        else:
            st.error("Please enter a valid email address.")

def reset_password(email):
    response = requests.post(f"{BACKEND_URL}/api/request-password-reset", json={"email": email})
    if response.status_code == 200:
        st.success("If a user with that email exists, a password reset link has been sent.")
    else:
        st.error("Failed to send reset link. Please try again.")

def initialize_assistant():
    assistant_response = requests.get(
        f"{BACKEND_URL}/api/v1/assistant/get-assistant",
        params={
            "user_id": st.session_state.user_id,
            "org_id": st.session_state.org_id,
            "user_role": st.session_state.role,
            "user_nickname": st.session_state.nickname
        },
        headers=get_auth_header()
    )
    if assistant_response.status_code == 200:
        st.session_state["assistant_id"] = assistant_response.json()["assistant_id"]
    else:
        st.warning("Failed to initialize assistant. Some features may be limited.")

def verify_email(token):
    response = requests.get(f"{BACKEND_URL}/api/verify-email/{token}")
    if response.status_code == 200:
        st.success("Email verified successfully")
        st.info("You can now log in to your account")
    else:
        st.error(response.json().get("detail", "Email verification failed"))

def is_authenticated():
    if 'auth_status' not in st.session_state or (time.time() - st.session_state.get('auth_check_time', 0) > 300):  # Check every 5 minutes
        if 'token' in st.session_state:
            try:
                response = requests.get(f"{BACKEND_URL}/api/v1/auth/is_authenticated", headers=get_auth_header())
                st.session_state.auth_status = response.status_code == 200 and response.json().get('authenticated', False)
                st.session_state.auth_check_time = time.time()
            except requests.RequestException as e:
                st.warning(f"Failed to check authentication status: {str(e)}")
                st.session_state.auth_status = False
        else:
            st.session_state.auth_status = False
    return st.session_state.auth_status

def login(email, password):
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/login", 
            data={"username": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data.get('access_token')
            st.session_state.user_id = data.get('user_id')
            st.session_state.role = data.get('role')
            st.session_state.nickname = data.get('nickname')
            st.session_state.org_id = data.get('org_id')
            st.session_state.is_admin = data.get('is_admin')
            st.session_state.is_super_admin = data.get('is_super_admin')
            st.session_state.authenticated = True
            st.session_state.auth_status = True
            st.session_state.auth_check_time = time.time()

            initialize_assistant()
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error(response.json().get("detail", "Login failed"))
    except requests.RequestException as e:
        st.error(f"An error occurred during login: {str(e)}")

def logout():
    try:
        if 'token' in st.session_state:
            requests.post(f"{BACKEND_URL}/api/v1/auth/logout", headers=get_auth_header())
    except requests.RequestException as e:
        st.warning(f"An error occurred during logout: {str(e)}")
    finally:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Logged out successfully!")
        st.rerun()

def login_form():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        org_config = get_org_public_config(client_name)
        main_image = get_main_image(client_name)

        if main_image:            
            st.image(main_image, width=200)
        elif org_config and 'name' in org_config:
            st.title(org_config['name'])
        else:
            st.title("Welcome")

        tab1, tab2, tab3 = st.tabs(["Login", "Register", "Reset Password"])

        with tab1:
            email = st.text_input("Email", key="login_email", value="suren@kr8it.com")
            password = st.text_input("Password", type="password", key="login_password", value="Sur3n#12")
            if st.button("Log In"):
                if validate_email(email) and password:
                    login(email, password)
                else:
                    st.error("Please enter a valid email and password.")
        
        st.divider()
        
        with tab2:
            register_form(org_config)

        with tab3:
            reset_password_form()
            
if __name__ == "__main__":
    if not is_authenticated():
        login_form()
    else:
        st.success("You are already logged in.")
        if st.button("Logout"):
            logout()
            st.rerun()