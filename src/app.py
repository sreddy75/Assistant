import random
import time
import requests
import streamlit as st
import base64
from ui.components.layout import set_page_layout
from ui.components.sidebar import render_sidebar
from ui.components.chat import render_chat, debug_knowledge_base
from utils.auth import BACKEND_URL, login, logout, is_authenticated, login_required, register, request_password_reset, reset_password, is_valid_email, verify_email
import logging
from queue import Queue
from threading import Thread
from streamlit_autorefresh import st_autorefresh
from utils.auth import get_user_id

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create a queue to hold initialization events
init_queue = Queue()

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
    
def login_form():
    st.title("Welcome to Compare the Meerkat!")
    col1, col2, col3 = st.columns([1,8,1])
    with col2:        
        file_ = open("images/meerkat.png", "rb")
        contents = file_.read()
        data_url = base64.b64encode(contents).decode("utf-8")
        file_.close()

        st.markdown(
            f'<div style="display: flex; justify-content: center; margin-bottom: 20px;">'
            f'<img src="data:image/png;base64,{data_url}" alt="meerkat logo" width="200">'
            f'</div>',
            unsafe_allow_html=True,
        )

        tab1, tab2, tab3 = st.tabs(["Login", "Register", "Reset Password"])
        
        with tab1:
            email = st.text_input("Email", key="login_email", value="suren@kr8it.com")
            password = st.text_input("Password", type="password", key="login_password", value="Sur3n#12")
            if st.button("Log In"):
                if is_valid_email(email):
                    if login(email, password):
                        st.session_state.authenticated = True
                        st.session_state.initialization_complete = False
                        st.session_state.user_id = get_user_id(email) 
                        logger.debug("User authenticated, initializing app")
                        st.rerun()
                    else:
                        st.error("Invalid email or password")
                else:
                    st.error("Please enter a valid email address")

        with tab2:
            new_email = st.text_input("Email", key="register_email")
            new_password = st.text_input("Password", type="password", key="register_password")
            if st.button("Register"):
                if is_valid_email(new_email):
                    success, message = register(new_email, new_password)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("Please enter a valid email address")

        with tab3:
            reset_email = st.text_input("Email", key="reset_email")
            if st.button("Reset Password"):
                if is_valid_email(reset_email):
                    success, message = request_password_reset(reset_email)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("Please enter a valid email address")

@st.cache_resource
def perform_heavy_initialization():
    log_init_event("Setting up page layout...")
    set_page_layout()
    log_init_event("Initializing knowledge base...")
    # Add any other heavy initialization steps here
    log_init_event("Initialization complete!")


def initialize_app():
    if "app_initialized" not in st.session_state:
        logger.debug("Starting app initialization")
        
        # Initialize llm_id if it's not already set
        if "llm_id" not in st.session_state:
            st.session_state.llm_id = "gpt-4o"  
            logger.debug(f"Initialized llm_id with default value: {st.session_state.llm_id}")
        
        # Initialize react_assistant_enabled if it's not already set
        if "react_assistant_enabled" not in st.session_state:
            st.session_state.react_assistant_enabled = False
            
        # Create a centered column for the spinner and status messages
        col1, col2, col3 = st.columns([1, 6, 1])
        with col2:
            st.markdown("<h1 style='text-align: center;'>Activating Meerkats...</h1>", unsafe_allow_html=True)
            
            status_placeholder = st.empty()
            
            initialization_messages = [                                
                "Git pulling from burrow...",                
                "Containerizing meerkat snacks...",
                "Deploying anti-mongoose firewall...",
                "Optimizing tail recursion...",
                "Parsing meerkat squeaks...",
                "Overclocking tiny paw-cessors...",                
                "Untangling spaghetti code...",                
                "Buffering sandstorm data...",                
                "Caching bug locations...",
                "Pair programming with meerkats...",
                "Agile sprinting from eagles...",
                "Mocking mongoose objects...",
                "Stress testing sand castles..."
            ]

            # Insert CSS for animation
            css = """
            <style>
            @keyframes fadeInOut {
                0% { opacity: 0; }
                50% { opacity: 1; }
                100% { opacity: 0; }
            }

            .fade {
                animation: fadeInOut 3s infinite;
                color: #FF4136;
            }
            </style>
            """
            st.markdown(css, unsafe_allow_html=True)

            # Ensure the user sees multiple messages before initialization completes
            for _ in range(5):
                status_message = f"<h3 class='fade' style='text-align: center;'>{random.choice(initialization_messages)}</h3>"
                status_placeholder.markdown(status_message, unsafe_allow_html=True)
                time.sleep(3)  # Delay to allow users to see the message

            perform_heavy_initialization()

            # Final status message
            status_placeholder.markdown("<h3 style='text-align: center; color: #00FF00;'>Initialization complete!</h3>", unsafe_allow_html=True)
            time.sleep(1)

        st.session_state.initialization_complete = True
        st.session_state.app_initialized = True
        logger.debug("App initialization complete")
    else:
        logger.debug("App already initialized, skipping initialization")
        
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
            success, message = reset_password(token, new_password)
            if success:
                st.success(message)
                st.info("You can now log in with your new password")
                # Clear the token from query params
                st.query_params.clear()
                # Add a button to go to login page
                if st.button("Go to Login"):
                    st.rerun()
            else:
                st.error(message)
                
def verify_email_form():
    st.title("Email Verification")

    token = st.query_params.get("token", "")
    
    if token:
        success, message = verify_email(token)
        if success:
            st.success(message)
            st.info("Your email has been verified. You can now log in to your account.")
            # Clear the token from query params
            st.query_params.clear()
            # Add a button to go to login page
            if st.button("Go to Login"):
                st.rerun()
        else:
            st.error(message)
    else:
        st.error("Invalid verification link. Please check your email and try again.")                            

def check_token_validity():
    if 'token' in st.session_state:
        try:
            response = requests.get(f"{BACKEND_URL}/users/me", headers={"Authorization": f"Bearer {st.session_state['token']}"})
            if response.status_code != 200:
                logout()
                st.rerun()
            else:
                # Update email in session state
                st.session_state['email'] = response.json().get('email')
        except requests.exceptions.RequestException:
            logout()
            st.rerun()
            
def main_app():    
    col1, col2 = st.sidebar.columns([2, 1])

    # Display welcome message in the first (wider) column
    with col1:
        if 'email' in st.session_state:
            st.write(f"Hi, {st.session_state['email']}!")
        else:   
            st.write("Welcome!")

    # Display logout button in the second (narrower) column
    with col2:
        if st.button("Logout"):
            logout()
            st.session_state.pop('user_id', None)
            st.session_state.pop('email', None)
            st.rerun()
    
    st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)  # Add divider            
    
    render_chat(user_id=st.session_state.get('user_id'))
    
    render_sidebar()



def main():
    st.set_page_config(
        page_title="Compare the Meerkat Assistant",
        page_icon="favicon.png",
    )

    logger.debug("Starting Compare the Meerkat app")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        logger.debug("Setting initial authenticated state")

    if "initialization_complete" not in st.session_state:
        st.session_state.initialization_complete = False
        logger.debug("Setting initial initialization_complete state")

    if "logout" in st.query_params:
        logout()
        st.query_params.clear()
        # Clear user-specific session state
        st.session_state.pop('user_id', None)
        st.session_state.pop('email', None)
        logger.debug("User logged out, clearing session")
        st.rerun()

    if "message" in st.query_params:
        st.success(st.query_params["message"])
        st.query_params.clear()

    if "token" in st.query_params:
        if "verify" in st.query_params:
            verify_email_form()
        elif "reset" in st.query_params:
            reset_password_form()
        else:
            st.error("Invalid link. Please check your email and try again.")
    elif st.session_state.authenticated:
        if not st.session_state.initialization_complete:
            logger.debug("Starting app initialization")
            initialize_app()
            st.rerun()
        else:
            logger.debug("Rendering main app")
            main_app()
    else:
        logger.debug("Showing login form")
        login_form()

if __name__ == "__main__":
    main()