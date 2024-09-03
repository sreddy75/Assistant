import base64
from io import BytesIO
import streamlit as st
import requests
from utils.api import BACKEND_URL, get_auth_header
from utils.helpers import get_client_name, validate_email, validate_password

client_name = get_client_name()

def is_authenticated():
    """
    Check if the user is authenticated.

    Returns:
    bool: True if authenticated, False otherwise.
    """
    if 'token' in st.session_state:
        response = requests.get(f"{BACKEND_URL}/api/v1/auth/is_authenticated", headers=get_auth_header())
        return response.status_code == 200 and response.json().get('authenticated', False)
    return False

def login_form():
    """
    Display and handle the login form.
    """
    st.markdown("""
    <style>
    .login-form {
        max-width: 400px;
        margin: 0 auto;
        padding: 20px;
        background-color: #2b313e;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .login-form input {
        width: 100%;
        margin-bottom: 10px;
    }
    .login-form .stButton > button {
        width: 100%;
    }
    .separator {
        width: 100%;
        height: 2px;
        background-color: #4CAF50;
        margin: 1rem 0;
    }
    .centered-image {
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:

        data_url = get_main_image()

        st.markdown(
            f'<div class="centered-image">'
            f'<img src="data:image/png;base64,{data_url}" alt="organization logo" width="200">'
            f'</div>',
            unsafe_allow_html=True,
        )

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
            register_form()

        with tab3:
            reset_password_form()

def login(email, password):
    """
    Attempt to log in the user with provided credentials.

    Args:
    email (str): User's email
    password (str): User's password
    """
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

            initialize_assistant()
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error(response.json().get("detail", "Login failed"))
    except requests.RequestException as e:
        st.error(f"An error occurred during login: {str(e)}")

def logout():
    """
    Log out the current user.
    """
    if 'token' in st.session_state:
        requests.post(f"{BACKEND_URL}/api/logout", headers=get_auth_header())
    st.session_state.clear()

def register_form():
    """
    Display and handle the registration form.
    """
    new_email = st.text_input("Email", key="register_email")
    new_password = st.text_input("Password", type="password", key="register_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
    first_name = st.text_input("First Name", key="register_first_name")
    last_name = st.text_input("Last Name", key="register_last_name")
    nickname = st.text_input("Nickname", key="register_nickname")

    # Fetch available roles
    response = requests.get(f"{BACKEND_URL}/api/v1/organizations/{client_name}/roles")
    if response.status_code == 200:
        available_roles = response.json()["roles"]
        role = st.selectbox("Role", options=available_roles, key="register_role")
    else:
        st.error("Unable to fetch roles. Please try again later.")
        role = None

    if st.button("Register"):
        if validate_email(new_email) and validate_password(new_password):
            if new_password == confirm_password:
                register(new_email, new_password, first_name, last_name, nickname, role)
            else:
                st.error("Passwords do not match.")
        else:
            st.error("Please enter a valid email and a strong password.")

def register(email, password, first_name, last_name, nickname, role):
    """
    Attempt to register a new user with provided information.

    Args:
    email (str): User's email
    password (str): User's password
    first_name (str): User's first name
    last_name (str): User's last name
    nickname (str): User's nickname
    role (str): User's role
    """
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
    """
    Display and handle the password reset form.
    """
    reset_email = st.text_input("Email", key="reset_email")
    if st.button("Reset Password"):
        if validate_email(reset_email):
            reset_password(reset_email)
        else:
            st.error("Please enter a valid email address.")

def reset_password(email):
    """
    Attempt to initiate a password reset for the provided email.

    Args:
    email (str): User's email
    """
    response = requests.post(f"{BACKEND_URL}/api/request-password-reset", json={"email": email})
    if response.status_code == 200:
        st.success("If a user with that email exists, a password reset link has been sent.")
    else:
        st.error("Failed to send reset link. Please try again.")

def initialize_assistant():
    """
    Initialize the assistant after successful login.
    """
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
    """
    Verify a user's email with the provided token.

    Args:
    token (str): Email verification token
    """
    response = requests.get(f"{BACKEND_URL}/api/verify-email/{token}")
    if response.status_code == 200:
        st.success("Email verified successfully")
        st.info("You can now log in to your account")
    else:
        st.error(response.json().get("detail", "Email verification failed"))

def get_main_image():
    """
    Fetch the main image from the organization's assets.
    
    Returns:
    str: Base64 encoded image data
    """
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/organizations/asset/{client_name}/login-form/main_image")
        if response.status_code == 200:
            image_data = BytesIO(response.content)
            contents = image_data.getvalue()
            data_url = base64.b64encode(contents).decode("utf-8")
            return data_url
        else:
            st.error(f"Failed to load organization image. Status code: {response.status_code}")
            return ""
    except requests.RequestException as e:
        st.error(f"Failed to fetch organization image: {str(e)}")
        return ""