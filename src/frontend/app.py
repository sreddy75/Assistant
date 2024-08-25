from io import BytesIO
import json
import pandas as pd
import streamlit as st
import requests
import base64
import logging
from datetime import datetime
import time
from queue import Queue
from ui.components.settings_manager import render_settings_tab
from src.backend.core.client_config import load_theme, ENABLED_ASSISTANTS, get_client_name
from ui.components.chat_interface import render_chat
from ui.components.analytics_dashboard import render_analytics_dashboard
from ui.components.dashboard_page import render_dashboard_analytics
from ui.components.knowledge_base import knowledge_base_page
from src.backend.core.config import settings

import toml

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create a queue to hold initialization events
init_queue = Queue()

BACKEND_URL = "http://localhost:8000"  

@st.cache_resource
def load_meerkat_logo():
    file_ = open("images/meerkat.png", "rb")
    contents = file_.read()
    data_url = base64.b64encode(contents).decode("utf-8")
    file_.close()
    return data_url

def log_init_event(event):
    init_queue.put(event)
    logger.debug(event)

def get_available_roles(org_name: str):
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/organizations/{org_name}/roles")
        response.raise_for_status()
        return response.json()["roles"]
    except requests.RequestException as e:
        st.error(f"Failed to fetch roles: {str(e)}")
        return []

def login_form():
    client_name = get_client_name()
    col1, col2, col3 = st.columns([1,8,1])
    with col2:
        # Fetch the main image from the organization's assets
        try:
            response = requests.get(f"{BACKEND_URL}/api/v1/organizations/asset/{client_name}/login-form/main_image")
            if response.status_code == 200:
                image_data = BytesIO(response.content)
                contents = image_data.getvalue()
                data_url = base64.b64encode(contents).decode("utf-8")
                
                st.markdown(
                    f'<div style="display: flex; justify-content: center; margin-bottom: 20px;">'
                    f'<img src="data:image/png;base64,{data_url}" alt="organization logo" width="200">'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.error(f"Failed to load organization image. Status code: {response.status_code}")
        except requests.RequestException as e:
            st.error(f"Failed to fetch organization image: {str(e)}")

        tab1, tab2, tab3 = st.tabs(["Login", "Register", "Reset Password"])        
        with tab1:
            email = st.text_input("Email", key="login_email", value="suren@kr8it.com")
            password = st.text_input("Password", type="password", key="login_password", value="Sur3n#12")
            if st.button("Log In"):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/api/v1/auth/login", 
                        data={"username": email, "password": password}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"Login successful for user: {email}")
                        
                        # Set session state variables
                        st.session_state.token = data.get('access_token')
                        st.session_state.user_id = data.get('user_id')
                        st.session_state.role = data.get('role')
                        st.session_state.nickname = data.get('nickname')
                        st.session_state.org_id = data.get('org_id')
                        st.session_state.is_admin = data.get('is_admin')
                        st.session_state.is_super_admin = data.get('is_super_admin')
                        st.session_state.authenticated = True

                        # Log the session state for debugging
                        logger.info(f"Session state after login: {st.session_state}")

                        st.success("Logged in successfully!")
                        st.experimental_rerun()
                    else:
                        error_msg = response.json().get("detail", "Login failed")
                        logger.error(f"Login failed for user {email}: {error_msg}")
                        st.error(error_msg)
                except requests.RequestException as e:
                    logger.error(f"Login request failed: {str(e)}")
                    st.error(f"An error occurred during login: {str(e)}")

        with tab2:
            new_email = st.text_input("Email", key="register_email")
            new_password = st.text_input("Password", type="password", key="register_password")
            first_name = st.text_input("First Name", key="register_first_name")
            last_name = st.text_input("Last Name", key="register_last_name")
            nickname = st.text_input("Nickname", key="register_nickname")
            
            org_name = get_client_name()
            available_roles = get_available_roles(org_name)
            if available_roles:
                role = st.selectbox("Role", options=available_roles, key="register_role")
            else:
                st.error("Unable to fetch roles. Please try again later.")
                role = None
            
            if st.button("Register"):
                response = requests.post(
                    f"{BACKEND_URL}/api/register",
                    json={
                        "email": new_email,
                        "password": new_password,
                        "first_name": first_name,
                        "last_name": last_name,
                        "nickname": nickname,
                        "role": role
                    },
                    params={"org_name": org_name}
                )
                if response.status_code == 200:
                    st.success("Registration successful! Please check your email for verification.")
                else:
                    st.error(response.json().get("detail", "Registration failed"))

        with tab3:
            reset_email = st.text_input("Email", key="reset_email")
            if st.button("Reset Password"):
                response = requests.post(f"{BACKEND_URL}/api/request-password-reset", json={"email": reset_email})
                if response.status_code == 200:
                    st.success("If a user with that email exists, a password reset link has been sent.")
                else:
                    st.error("Failed to send reset link. Please try again.")

def initialize_app():
    if "app_initialized" not in st.session_state:
        logger.debug("Starting app initialization")
        
        if "llm_id" not in st.session_state:
            st.session_state.llm_id = "gpt-4o"
            logger.debug(f"Initialized llm_id with default value: {st.session_state.llm_id}")
        
        for assistant in ENABLED_ASSISTANTS:
            key = f"{assistant.lower().replace(' ', '_')}_enabled"
            if key not in st.session_state:
                st.session_state[key] = True
                logger.debug(f"Initialized {key} with default value: True")
        
        perform_heavy_initialization()
        
        st.session_state.initialization_complete = True
        st.session_state.app_initialized = True
        logger.debug("App initialization complete")
    else:
        logger.debug("App already initialized, skipping initialization")

    st.rerun()

@st.cache_resource
def perform_heavy_initialization():
    log_init_event("Setting up page layout...")
    log_init_event("Initializing knowledge base...")
    # Add any other heavy initialization steps here
    log_init_event("Initialization complete!")

def reset_password_form():
    st.title("Reset Your Password")
    token = st.query_params.get("token", "")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")
    if st.button("Reset Password"):
        if new_password != confirm_password:
            st.error("Passwords do not match")
        elif len(new_password) < 8:
            st.error("Password must be at least 8 characters long")
        else:
            response = requests.post(f"{BACKEND_URL}/api/reset-password", json={"token": token, "new_password": new_password})
            if response.status_code == 200:
                st.success("Password reset successfully")
                st.info("You can now log in with your new password")
                st.query_params.clear()
                if st.button("Go to Login"):
                    st.rerun()
            else:
                st.error(response.json().get("detail", "Password reset failed"))

def verify_email_form():
    st.title("Email Verification")
    token = st.query_params.get("token", "")
    if token:
        response = requests.get(f"{BACKEND_URL}/api/verify-email/{token}")
        if response.status_code == 200:
            st.success("Email verified successfully")
            st.info("You can now log in to your account")
            st.query_params.clear()
            if st.button("Go to Login"):
                st.rerun()
        else:
            st.error(response.json().get("detail", "Email verification failed"))
    else:
        st.error("Invalid verification link. Please check your email and try again.")

def is_authenticated():
    if 'token' in st.session_state:
        response = requests.get(f"{BACKEND_URL}/api/v1/auth/is_authenticated", headers={"Authorization": f"Bearer {st.session_state['token']}"})
        return response.status_code == 200 and response.json().get('authenticated', False)
    return False

def logout():
    if 'token' in st.session_state:
        requests.post(f"{BACKEND_URL}/api/logout", headers={"Authorization": f"Bearer {st.session_state['token']}"})
    st.session_state.clear()

def main_app():
    col1, col2 = st.sidebar.columns([2, 1])
    with col1:
        if st.session_state.get('nickname'):            
            st.text(f"Welcome, {st.session_state.get('nickname')}")                    
            
    with col2:
        if st.button("Logout"):
            logout()
            st.rerun()

    tabs = ["Chat", "Knowledge Base"]
    if st.session_state.get('is_admin', False):
        pass
    if st.session_state.get('is_super_admin', False):
        tabs.append("Home")    
        tabs.append("Analytics")    
        tabs.append("Settings")    
    
    selected_tab = st.tabs(tabs)

    with selected_tab[tabs.index("Home")]:
        render_dashboard_analytics()
    
    with selected_tab[tabs.index("Chat")]:
        render_chat(user_id=st.session_state.get('user_id'), user_role=st.session_state.get('role'))

    with selected_tab[tabs.index("Knowledge Base")]:  
        knowledge_base_page() 

    if st.session_state.get('is_admin', False):
        with selected_tab[tabs.index("Analytics")]:  
            render_analytics_dashboard()
        
    if st.session_state.get('is_super_admin', False) and "Settings" in tabs:
        with selected_tab[tabs.index("Settings")]:
            render_settings_tab()

def apply_custom_theme():
    try:
        # Fetch the config.toml file content
        response = requests.get(f"{BACKEND_URL}/api/v1/organizations/public-config/{settings.CLIENT_NAME}")
        response.raise_for_status()

        # Parse the TOML content
        config_content = response.text
        theme_config = toml.loads(config_content)

        # Apply the theme
        theme_css = f"""
        <style>
            .stApp {{
                background-color: {theme_config['theme']['backgroundColor']};
            }}
            .stTextInput > div > div > input,
            .stTextArea > div > div > textarea,
            .stSelectbox > div > div > div {{
                color: {theme_config['theme']['textColor']};                
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                border: 1px solid {theme_config['theme']['primaryColor']};
                border-radius: 4px;
            }}
            /* Select box specific styling */
            .stSelectbox > div > div > div {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
            }}
            .stSelectbox > div > div::before {{
                background-color: {theme_config['theme']['primaryColor']};
            }}
            .stSelectbox > div > div > div:hover {{
                border-color: {theme_config['theme']['primaryColor']};
            }}
            .stSelectbox > div > div > div[aria-selected="true"] {{
                background-color: {theme_config['theme']['primaryColor']};
                color: {theme_config['theme']['backgroundColor']};
            }}
            /* Dropdown menu styling */
            .stSelectbox [data-baseweb="select"] {{
                z-index: 999;
            }}
            .stSelectbox [data-baseweb="menu"] {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
            }}
            .stSelectbox [data-baseweb="option"] {{
                color: {theme_config['theme']['textColor']};
            }}
            .stSelectbox [data-baseweb="option"]:hover {{
                background-color: {theme_config['theme']['primaryColor']};
                color: {theme_config['theme']['backgroundColor']};
            }}
            .stButton > button {{
                color: {theme_config['theme']['backgroundColor']};
                background-color: {theme_config['theme']['primaryColor']};
                border: none;
                border-radius: 4px;
                padding: 0.5rem 1rem;
                font-weight: bold;
            }}
            .stButton > button:hover {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                color: {theme_config['theme']['primaryColor']};
            }}
            * {{
                font-family: {theme_config['theme']['font']};
            }}
            /* Tab styling */
            .stTabs {{
                background-color: {theme_config['theme']['backgroundColor']};
            }}
            .stTabs [data-baseweb="tab-list"] {{
                gap: 25px;
                background-color: {theme_config['theme']['backgroundColor']};
                border-radius: 4px;
                padding: 0.5rem;
            }}
            .stTabs [data-baseweb="tab"] {{
                height: 50px;
                background-color: {theme_config['theme']['backgroundColor']};
                border-radius: 4px;
                color: {theme_config['theme']['textColor']};
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            .stTabs [aria-selected="true"] {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                color: {theme_config['theme']['backgroundColor']};
            }}
            .stTabs [data-baseweb="tab"]:hover {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                color: {theme_config['theme']['backgroundColor']};
                font-weight: 800;
                opacity: 0.8;
            }}
            /* Expander styling */
            .streamlit-expanderHeader {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                color: {theme_config['theme']['textColor']};
                border-radius: 4px;
                border: 1px solid {theme_config['theme']['primaryColor']};
                padding: 0.5rem;
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            .streamlit-expanderHeader:hover {{
                background-color: {theme_config['theme']['primaryColor']};
                color: {theme_config['theme']['backgroundColor']};
            }}
            .streamlit-expanderContent {{
                background-color: {theme_config['theme']['backgroundColor']};
                color: {theme_config['theme']['textColor']};
                border: 1px solid {theme_config['theme']['primaryColor']};
                border-top: none;
                border-radius: 0 0 4px 4px;
                padding: 0.5rem;
            }}
            /* Checkbox styling */
            .stCheckbox > label > span {{
                color: {theme_config['theme']['textColor']};
            }}
            .stCheckbox > label > div[data-baseweb="checkbox"] {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
            }}
            .stCheckbox > label > div[data-baseweb="checkbox"] > div {{
                background-color: {theme_config['theme']['primaryColor']};
            }}
            /* Slider styling */
            .stSlider > div > div > div > div {{
                background-color: {theme_config['theme']['primaryColor']};
            }}
            .stSlider > div > div > div > div > div {{
                color: {theme_config['theme']['backgroundColor']};
            }}
        </style>
        """
        st.markdown(theme_css, unsafe_allow_html=True)

    except requests.HTTPError as e:
        logger.error(f"HTTP error occurred while fetching config: {e}")
        st.error("An error occurred while applying the theme. Using default theme.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while applying theme: {e}")
        st.error("An error occurred while applying the theme. Using default theme.")
                
def main():
    apply_custom_theme()
    
    if not is_authenticated():
        login_form()
    else:
        if not st.session_state.get("initialization_complete", False):
            initialize_app()
        else:
            main_app()

if __name__ == "__main__":
        main()