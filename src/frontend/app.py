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
from ui.components.sidebar_manager import render_sidebar
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

# Setting page config @ beginning
st.set_page_config(layout="wide")

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
    
    # Custom CSS for the login form
    st.markdown("""
    <style>
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
    }
    .login-form {
        width: 300px;
        padding: 20px;
        background-color: #2b313e;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .login-form input {
        width: 100%;
        margin-bottom: 10px;
        padding: 8px;
        border: 1px solid #4CAF50;
        border-radius: 4px;
        background-color: #1E1E1E;
        color: white;
    }
    .login-form .stButton > button {
        width: 100%;
        margin-top: 10px;
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
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        white-space: nowrap;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:                
        # Fetch the main image from the organization's assets
        try:
            response = requests.get(f"{BACKEND_URL}/api/v1/organizations/asset/{client_name}/login-form/main_image")
            if response.status_code == 200:
                image_data = BytesIO(response.content)
                contents = image_data.getvalue()
                data_url = base64.b64encode(contents).decode("utf-8")
                
                st.markdown(
                    f'<div class="centered-image">'
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
            st.markdown('<div class="separator"></div>', unsafe_allow_html=True)
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

                        # Fetch the assistant from the backend
                        assistant_response = requests.get(
                            f"{BACKEND_URL}/api/v1/assistant/get-assistant",
                            params={
                                "user_id": st.session_state.user_id,
                                "org_id": st.session_state.org_id,
                                "user_role": st.session_state.role,
                                "user_nickname": st.session_state.nickname
                            },
                            headers={"Authorization": f"Bearer {st.session_state.token}"}
                        )
                        if assistant_response.status_code == 200:
                            st.session_state["assistant_id"] = assistant_response.json()["assistant_id"]
                            st.success("Logged in successfully and assistant initialized!")
                        else:
                            st.warning("Logged in successfully, but failed to initialize assistant. Some features may be limited.")
                        
                        st.experimental_rerun()
                    else:
                        error_msg = response.json().get("detail", "Login failed")
                        logger.error(f"Login failed for user {email}: {error_msg}")
                        st.error(error_msg)
                except requests.RequestException as e:
                    logger.error(f"Login request failed: {str(e)}")
                    st.error(f"An error occurred during login: {str(e)}")

        with tab2:
            st.markdown('<div class="separator"></div>', unsafe_allow_html=True)
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
                    f"{BACKEND_URL}/api/v1/auth/register",
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
            st.markdown('<div class="separator"></div>', unsafe_allow_html=True)
            reset_email = st.text_input("Email", key="reset_email")
            if st.button("Reset Password"):
                response = requests.post(f"{BACKEND_URL}/api/request-password-reset", json={"email": reset_email})
                if response.status_code == 200:
                    st.success("If a user with that email exists, a password reset link has been sent.")
                else:
                    st.error("Failed to send reset link. Please try again.")

        st.markdown('</div>', unsafe_allow_html=True)

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
            /* Global styles */
            .stApp, .stApp p, .stApp label, .stApp .stMarkdown, .stApp .stText {{
                color: {theme_config['theme']['textColor']};
            }}
            .stApp {{
                background-color: {theme_config['theme']['backgroundColor']};
            }}
            * {{
                font-family: {theme_config['theme']['font']};
            }}

            /* Input fields */
            .stTextInput > div > div > input,
            .stTextArea > div > div > textarea,
            .stSelectbox > div > div > div,
            .stMultiSelect > div > div > div {{
                color: {theme_config['theme']['textColor']};                
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                border: 1px solid {theme_config['theme']['primaryColor']};
                border-radius: 4px;
            }}

            /* Select box */
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

            /* Dropdown menu */
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

            /* Buttons */
            .stButton > button {{
                color: {theme_config['theme']['backgroundColor']};                
                background-color: #25cf47;
                border: none;
                border-radius: 4px;
                padding: 0.5rem 1rem;
                font-weight: bold;
            }}
            .stButton > button:hover {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                color: {theme_config['theme']['primaryColor']};
            }}

            /* Tabs */
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
                color: {theme_config['theme']['secondaryBackgroundColor']};
            }}
            .stTabs [data-baseweb="tab"]:hover {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                color: {theme_config['theme']['backgroundColor']};
                font-weight: 800;
                opacity: 0.8;
            }}

            /* Expander */
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

            /* Checkbox */
            .stCheckbox > label > span {{
                color: {theme_config['theme']['textColor']};
            }}
            .stCheckbox > label > div[data-baseweb="checkbox"] {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
            }}
            .stCheckbox > label > div[data-baseweb="checkbox"] > div {{
                background-color: {theme_config['theme']['primaryColor']};
            }}

            /* Slider */
            .stSlider > div > div > div > div {{
                background-color: {theme_config['theme']['primaryColor']};
            }}
            .stSlider > div > div > div > div > div {{
                color: {theme_config['theme']['backgroundColor']};
            }}

            /* Table */
            .dataframe {{
                color: {theme_config['theme']['textColor']} !important;
            }}
            .dataframe th {{
                color: {theme_config['theme']['textColor']} !important;
            }}
            .dataframe td {{
                color: {theme_config['theme']['textColor']} !important;
            }}

            /* File uploader */
            .stFileUploader > div > div {{
                color: {theme_config['theme']['textColor']} !important;
            }}

            /* Info, warning, and error messages */
            .stAlert > div {{
                color: {theme_config['theme']['textColor']} !important;
            }}

            /* Sidebar styling */
            [data-testid="stSidebar"] {{
                background-color: #292727;
            }}
            [data-testid="stSidebar"] .stButton > button {{
                background-color: #25cf47;
                color: white;
            }}
            [data-testid="stSidebar"] .stTextInput > div > div > input {{
                background-color: #3E3E3E;
                color: white;
            }}
            [data-testid="stSidebar"] .stSelectbox > div > div > div {{
                background-color: #3E3E3E;
                color: white;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
                color: white;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {{
                color: white;
            }}
            [data-testid="stSidebar"] .stCheckbox > label > span {{
                color: white;
            }}

            /* Hide Streamlit Hamburger Menu and "Deploy" Button */
            .stApp > header {{
                display: none !important;
            }}

            /* Adjust the main content area to take up the space of the removed header */
            .stApp > .main {{
                margin-top: -4rem;
            }}

            /* Chat message styling */
            .chat-message, .chat-message p, .chat-message li, .chat-message h1, .chat-message h2, .chat-message h3, .chat-message h4, .chat-message h5, .chat-message h6 {{
                color: white !important;
            }}
            .assistant-response, .assistant-response p, .assistant-response li, .assistant-response h1, .assistant-response h2, .assistant-response h3, .assistant-response h4, .assistant-response h5, .assistant-response h6 {{
                color: white !important;
            }}
            .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {{
                color: white !important;
            }}

            /* Pulsating dot animation */
            @keyframes pulse {{
                0% {{ transform: scale(0.8); opacity: 0.7; }}
                50% {{ transform: scale(1); opacity: 1; }}
                100% {{ transform: scale(0.8); opacity: 0.7; }}
            }}
            .pulsating-dot {{
                width: 20px; height: 20px;
                background-color: #ff0000;
                border-radius: 50%;
                display: inline-block;
                animation: pulse 1.5s ease-in-out infinite;
            }}

            /* Separator for tabs */
            .separator {{
                width: 100%;
                height: 2px;
                background-color: red;
                margin: 1rem 0;
            }}
            
              /* Comprehensive Slider Styling */
            .stSlider label,
            .stSlider text,
            .stSlider .st-bb,
            .stSlider .st-bv,
            .stSlider .st-cj,
            .stSlider .st-cl,
            .stSlider [data-baseweb="slider"] {{
                color: white !important;
            }}
            
            /* Ensure all text within the slider container is white */
            [data-testid="stSlider"] {{
                color: white !important;
            }}
            
            /* Target specific parts of the slider */
            [data-testid="stSlider"] > div > div > div {{
                color: white !important;
            }}
            
            /* Slider thumb label */
            [data-testid="stSlider"] [data-testid="stThumbValue"] {{
                color: white !important;
            }}
            
             /* Enhanced Expander Styling */
            .streamlit-expanderHeader {{
                background-color: {theme_config['theme']['primaryColor']};
                color: {theme_config['theme']['backgroundColor']};
                border-radius: 8px 8px 0 0;
                border: 2px solid {theme_config['theme']['primaryColor']};
                padding: 0.75rem 1rem;
                font-weight: 600;
                font-size: 1.1em;
                transition: all 0.3s ease;
                margin-top: 1rem;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .streamlit-expanderHeader:hover {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                color: {theme_config['theme']['primaryColor']};
            }}
            .streamlit-expanderContent {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                color: {theme_config['theme']['textColor']};
                border: 2px solid {theme_config['theme']['primaryColor']};
                border-top: none;
                border-radius: 0 0 8px 8px;
                padding: 1rem;
                margin-bottom: 1rem;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            
            /* Expander icon styling */
            .streamlit-expanderHeader svg {{
                transform: scale(1.5);
                fill: {theme_config['theme']['backgroundColor']};
                transition: all 0.3s ease;
            }}
            .streamlit-expanderHeader:hover svg {{
                fill: {theme_config['theme']['primaryColor']};
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

def apply_expander_style():
    expander_style = """
    <style>
        /* Enhanced Expander Styling */
        [data-testid="stExpander"] {
            border: 2px solid #4CAF50;
            border-radius: 8px;
            margin-top: 1rem;
            margin-bottom: 1rem;
        }
        [data-testid="stExpander"] > div:first-child {
            background-color: #4CAF50;
            color: white;
            padding: 0.75rem 1rem;
            font-weight: 600;
            font-size: 1.1em;
            transition: all 0.3s ease;
            border-radius: 6px 6px 0 0;
        }
        [data-testid="stExpander"] > div:first-child:hover {
            background-color: #45a049;
        }
        [data-testid="stExpander"] > div:nth-child(2) {
            background-color: #1E1E1E;
            color: white;
            border-top: none;
            border-radius: 0 0 6px 6px;
            padding: 1rem;
        }
        [data-testid="stExpander"] svg {
            transform: scale(1.5);
            fill: white;
            transition: all 0.3s ease;
        }
        [data-testid="stExpander"]:hover svg {
            fill: #E0E0E0;
        }
    </style>
    """
    st.markdown(expander_style, unsafe_allow_html=True)

def maximize_content_area():
    # Hide the main menu and footer
    hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stApp {
            max-width: 100%;
            padding-top: 0rem;
        }
        .main .block-container {
            max-width: 100%;
            padding-top: 1rem;
            padding-right: 1rem;
            padding-left: 1rem;
            padding-bottom: 1rem;
        }
        .sidebar .sidebar-content {
            width: 300px;
        }
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

def main_app():
    st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">', unsafe_allow_html=True)    
    apply_expander_style()

    # Sidebar
    with st.sidebar:
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.session_state.get('nickname'):            
                st.text(f"Welcome, {st.session_state.get('nickname')}")                    
        with col2:
            if st.button("Logout"):
                logout()
                st.rerun()

    # Main content area
    col1, col2, col3 = st.columns([1, 6, 1])
    
    with col2:
        tabs = ["Chat", "Knowledge Base"]
        if st.session_state.get('is_admin', False):
            tabs.append("Analytics")
        if st.session_state.get('is_super_admin', False):
            tabs.extend(["Home", "Settings"])
        
        selected_tab = st.tabs(tabs)

        for i, tab in enumerate(tabs):
            with selected_tab[i]:
                st.markdown('<div class="separator"></div>', unsafe_allow_html=True)
                
                if tab == "Home":
                    render_dashboard_analytics()
                elif tab == "Chat":
                    render_chat(user_id=st.session_state.get('user_id'), user_role=st.session_state.get('role'))
                    render_sidebar()
                elif tab == "Knowledge Base":
                    knowledge_base_page()
                elif tab == "Analytics":
                    render_analytics_dashboard()
                elif tab == "Settings":
                    render_settings_tab()                                            
def main():
    
    apply_custom_theme()
    maximize_content_area()
    
    if not is_authenticated():
        login_form()
    else:
        if not st.session_state.get("initialization_complete", False):
            initialize_app()
        else:
            main_app()

if __name__ == "__main__":
        main()