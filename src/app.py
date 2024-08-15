
from collections import defaultdict
import datetime
import socket
import time
import pandas as pd
import requests
import streamlit as st
import base64
from streamlit.web.server.websocket_headers import _get_websocket_headers
from ui.components.layout import set_page_layout
from ui.components.sidebar import render_sidebar
from ui.components.chat import render_chat
from utils.auth import BACKEND_URL, login, logout, register, request_password_reset, reset_password, is_valid_email, verify_email
import logging
from utils.auth import get_all_users, extend_user_trial
from queue import Queue
from utils.auth import get_user_id
import time
from service.analytics_service import analytics_service
from config.client_config import load_theme, ENABLED_ASSISTANTS, get_client_name
import toml

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
    client_name = get_client_name()         
    col1, col2, col3 = st.columns([1,8,1])
    with col2:        
        # Customize the app based on the client                   
        st.markdown(f"<h1 style='color: white; text-align: center;'>{client_name.upper()}'s Assistant</h1>", unsafe_allow_html=True)
        file_ = open(f"src/config/themes/{get_client_name()}/main_image.png", "rb")
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
            password = st.text_input("Password", type="password", key="login_password", value="password")
            st.session_state.is_admin = is_admin_user(email)
            if st.button("Log In"):
                if is_valid_email(email):
                    login_result = login(email, password)
                    if login_result == True:
                        st.session_state.authenticated = True
                        st.session_state.initialization_complete = False
                        st.session_state.user_id = get_user_id(email)                        
                        
                        # Set admin flag
                        st.session_state.is_admin = is_admin_user(email)
                        
                        logger.debug("User authenticated, initializing app")
                        st.rerun()
                    elif login_result == "Trial period has ended":
                        st.markdown("""
                            <style>
                            .custom-error {
                                padding: 1rem;
                                border-radius: 0.5rem;
                                background-color: #f5f1f0;
                                color: #d12f06;
                            }
                            </style>
                            """, unsafe_allow_html=True)

                        st.markdown('<div class="custom-error">Your trial period has ended. Please contact support to extend your trial or upgrade your account.</div>', unsafe_allow_html=True)
                    else:
                        st.error("Invalid email or password")
                else:
                    st.error("Please enter a valid email address")
                    

        with tab2:
            new_email = st.text_input("Email", key="register_email")
            new_password = st.text_input("Password", type="password", key="register_password")
            first_name = st.text_input("First Name", key="register_first_name")
            last_name = st.text_input("Last Name", key="register_last_name")
            nickname = st.text_input("Nickname", key="register_nickname")
            role = st.selectbox("Role", options=["QA", "Dev", "Product", "Delivery", "Manager"], key="register_role")
            
            if st.button("Register"):
                if is_valid_email(new_email):
                    if first_name and last_name and nickname:
                        success, message = register(new_email, new_password, first_name, last_name, nickname, role)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill in all fields.")
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


def is_admin_user(email):
    try:
        response = requests.get(f"{BACKEND_URL}/users/{email}/is-admin", headers={"Authorization": f"Bearer {st.session_state['token']}"})
        if response.status_code == 200:
            return response.json()["is_admin"]
        else:
            logger.error(f"Failed to check admin status: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error checking admin status: {str(e)}")
        return False
    
import time
import random
import streamlit as st

def initialize_app():
    if "app_initialized" not in st.session_state:
        logger.debug("Starting app initialization")
        
        # Initialize llm_id if it's not already set
        if "llm_id" not in st.session_state:
            st.session_state.llm_id = "gpt-4o"  
            logger.debug(f"Initialized llm_id with default value: {st.session_state.llm_id}")
        
        # Initialize assistant states based on ENABLED_ASSISTANTS
        for assistant in ENABLED_ASSISTANTS:
            key = f"{assistant.lower().replace(' ', '_')}_enabled"
            if key not in st.session_state:
                st.session_state[key] = True
                logger.debug(f"Initialized {key} with default value: True")        
        
        # Create a centered column for the spinner and status messages
        col1, col2, col3 = st.columns([1, 6, 1])
        with col2:
            # CSS for animations
            st.markdown("""
            <style>
            @keyframes fadeInOut {
                0% { opacity: 0; }
                50% { opacity: 1; }
                100% { opacity: 0; }
            }
            @keyframes slideIn {
                from { transform: translateY(-20px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            .fade {
                animation: fadeInOut 2s infinite;
            }
            .slide-in {
                animation: slideIn 0.5s ease-out;
            }
            .status-message {
                text-align: center;
                color: #fcf8f7;
                font-size: 1.5em;
                margin-bottom: 20px;
            }
            .final-message {
                text-align: center;
                color: #75ffa5;
                font-size: 2em;
                font-weight: bold;
            }
            </style>
            """, unsafe_allow_html=True)
            
            main_title = st.empty()
            status_placeholder = st.empty()
            progress_bar = st.progress(0)

            initialization_messages = [
                "Initializing language models...",
                "Loading knowledge base...",
                "Configuring assistants...",
                "Preparing natural language processing...",
                "Optimizing algorithms...",
                "Setting up sentiment analysis...",
                "Loading conversation history...",
                "Configuring analytics..."
            ]

            main_title.markdown("<h1 class='slide-in' style='text-align: center; color: #e67529;'>Initializing</h1>", unsafe_allow_html=True)

            for i, message in enumerate(initialization_messages):
                status_placeholder.markdown(f"<p class='status-message fade'>{message}</p>", unsafe_allow_html=True)
                progress = (i + 1) / len(initialization_messages)
                progress_bar.progress(progress)
                time.sleep(0.5)  # Reduced delay for faster initialization

            perform_heavy_initialization()

            # Final status message
            main_title.empty()
            status_placeholder.empty()
            progress_bar.empty()            
        
        st.session_state.initialization_complete = True
        st.session_state.app_initialized = True
        logger.debug("App initialization complete")
    else:
        logger.debug("App already initialized, skipping initialization")

    # Smooth transition to main app
    st.empty()  # Clear the initialization messages
    st.rerun()  # Rerun the app to show the main interface
                    
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

def render_settings_tab():
    st.header("User Management")
    
    # Display any stored messages
    if "trial_extension_messages" in st.session_state:
        for message, is_error in st.session_state["trial_extension_messages"]:
            if is_error:
                st.error(message)
            else:
                st.success(message)
        # Clear the messages after displaying
        st.session_state.pop("trial_extension_messages")

    # Fetch all users from the database
    users = get_all_users()
    
    if not users:
        st.warning("No users found in the database.")
        return
    
    # Create a dataframe from the user data
    df = pd.DataFrame(users)
    
    # Convert Trial End Date to datetime if it's not already
    df['trial_end'] = pd.to_datetime(df['trial_end'])
    
    # Add an "Extend Trial" button column
    df['Extend Trial'] = False

    # Render the interactive dataframe
    edited_df = st.data_editor(
        df,
        column_config={
            "id": st.column_config.NumberColumn("ID"),
            "email": st.column_config.TextColumn("Email"),
            "role": st.column_config.TextColumn("Role"),
            "trial_end": st.column_config.DatetimeColumn("Trial End Date"),
            "is_active": st.column_config.CheckboxColumn("Is Active"),
            "Extend Trial": st.column_config.CheckboxColumn("Extend Trial")
        },
        disabled=["id", "email", "role", "trial_end", "is_active"],
        hide_index=True,
    )
    
    # Check if any trials need to be extended
    changes_made = False
    messages = []
    for index, row in edited_df.iterrows():
        if row['Extend Trial']:
            user_id = row['id']
            if extend_user_trial(user_id):
                messages.append((f"Trial extended for {row['email']} by 7 days", False))
                # Update the trial end date in the dataframe
                edited_df.at[index, 'trial_end'] += datetime.timedelta(days=7)
                changes_made = True
            else:
                messages.append((f"Failed to extend trial for {row['email']}", True))
            # Reset the checkbox
            edited_df.at[index, 'Extend Trial'] = False
    
    # If any changes were made, store the messages and rerun
    if changes_made:
        st.session_state["trial_extension_messages"] = messages
        st.experimental_rerun()
    elif messages:
        # If there were only error messages, display them immediately
        for message, is_error in messages:
            if is_error:
                st.error(message)
            else:
                st.success(message)

def get_user_documents(user_id):
    try:
        llm_os = st.session_state.get("llm_os")
        if not llm_os or not hasattr(llm_os, 'knowledge_base') or not llm_os.knowledge_base or not hasattr(llm_os.knowledge_base, 'vector_db'):
            logger.warning("LLM OS or knowledge base not properly initialized")
            return []
        
        if not hasattr(llm_os.knowledge_base.vector_db, 'list_document_names'):
            logger.warning("Vector database does not have a list_document_names method")
            return []
        
        document_names = llm_os.knowledge_base.vector_db.list_document_names()
        
        # Group document chunks
        grouped_documents = defaultdict(int)
        for name in document_names:
            base_name = name.split('_chunk_')[0] if '_chunk_' in name else name
            grouped_documents[base_name] += 1
        
        # Create a list of unique document names with chunk counts
        unique_documents = [f"{name} ({count} chunks)" if count > 1 else name for name, count in grouped_documents.items()]
        
        return unique_documents
    except Exception as e:
        logger.error(f"Error retrieving user documents: {str(e)}", exc_info=True)
        return []
                                
def main_app():
    col1, col2 = st.sidebar.columns([2, 1])

    with col1:
        if 'email' in st.session_state:
            st.write(f"Hi, {st.session_state['email']}!")
        else:   
            st.write("Welcome!")

    with col2:
        if st.button("Logout"):
            logout()
            st.session_state.pop('user_id', None)
            st.session_state.pop('email', None)
            st.session_state.pop('role', None)
            st.rerun()
    
    st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)

    # Determine which tabs to show based on user role
    tabs = ["Chat", "My Documents"]
    if st.session_state.get('is_admin', False):
        tabs.extend(["Analytics", "Settings"])
    
    selected_tab = st.tabs(tabs)

    with selected_tab[0]:  # Chat tab
        render_chat(user_id=st.session_state.get('user_id'), user_role=st.session_state.get('role'))

    with selected_tab[1]:  # My Documents tab
        st.header("My Uploaded Documents")
        if st.button("Refresh Document List"):
            st.session_state["user_documents"] = get_user_documents(st.session_state.get('user_id'))
        
        try:
            user_documents = st.session_state.get("user_documents", get_user_documents(st.session_state.get('user_id')))
            if user_documents:
                for doc in user_documents:
                    st.write(f"- {doc}")
            else:
                st.write("No documents uploaded yet.")
        except Exception as e:
            st.error(f"An error occurred while retrieving your documents: {str(e)}")
            logger.error(f"Error displaying user documents: {str(e)}", exc_info=True)
        

    if st.session_state.get('is_admin', False):
        with selected_tab[2]:  # Analytics tab
            from ui.components.chat import render_analytics_dashboard
            render_analytics_dashboard()
        
        with selected_tab[3]:  # Settings tab
            render_settings_tab()

    render_sidebar()

def apply_custom_theme():
    theme_path = load_theme()
    with open(theme_path, 'r') as f:
        theme_config = toml.load(f)
    
    # Apply the theme using custom CSS
    theme_css = f"""
    <style>
        .stApp {{
            background-color: {theme_config['theme']['backgroundColor']};
        }}
        .stTextInput > div > div > input {{
            color: white !important;
            background-color: black !important;
        }}
        .stButton > button {{
            color:  white !important;
            background-color: {theme_config['theme']['primaryColor']};
        }}
        .stTextArea > div > div > textarea {{
            color: {theme_config['theme']['textColor']};
        }}
         /* Selectbox (dropdown) */
        .stSelectbox > div > div > div {{
            color: white !important;
            background-color: black !important;
        }}
        .stHeader {{
            color: {theme_config['theme']['primaryColor']};
        }}
        * {{
            font-family: {theme_config['theme']['font']};
        }}
        /* Style for password input fields */
        input[type="password"] {{
            color: white !important;
            background-color: black !important;
        }}        
        /* Custom tab styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 20px;
            background-color: {theme_config['theme']['backgroundColor']};
        }}
        .stTabs [data-baseweb="tab"] {{
            height: 50px;
            background-color: {theme_config['theme']['backgroundColor']};
            border-radius: 4px 4px 0 0;
            gap: 5px;
            padding-top: 10px;
            padding-bottom: 10px;
            font-size: 16px;
            font-weight: 500;
            color: white !important;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: ;
            color: white;
        }}
    </style>
    """
    st.markdown(theme_css, unsafe_allow_html=True)

def get_client_ip():
    try:
        response = requests.get('https://api.ipify.org')
        return response.text
    except requests.RequestException:
        return "Unable to get IP"

def get_user_agent():
    return st.get_option("browser.serverAddress")

def get_hostname():
    try:
        return socket.gethostname()
    except:
        return "Unable to get hostname"

def hide_streamlit_style():
    hide_st_style = """
                <style>
                #MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
                header {visibility: hidden;}
                </style>
                """
    st.markdown(hide_st_style, unsafe_allow_html=True)
            
def main():
    
    st.set_page_config(
        page_title="AI Assistant", 
        page_icon="🤖"          
    )
    
     # Apply custom theme
    apply_custom_theme()    
    hide_streamlit_style()

    # Track user information
    if 'user_agent' not in st.session_state:
        st.session_state['user_agent'] = get_user_agent()

    if 'client_ip' not in st.session_state:
        st.session_state['client_ip'] = get_client_ip()

    if 'hostname' not in st.session_state:
        st.session_state['hostname'] = get_hostname()            
    
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
            if st.session_state.authenticated:
                user_id = st.session_state.get('user_id')
                
                # Log app access
                analytics_service.log_event(user_id, "app_access", {
                    "user_agent": st.session_state.get('user_agent', ''),
                    "ip_address": st.session_state.get('client_ip', ''),
                    "hostname": st.session_state.get('hostname', '')
                })

                if not st.session_state.initialization_complete:
                    start_time = time.time()
                    initialize_app()
                    
                    # Log app initialization
                    analytics_service.log_event(user_id, "app_initialized", {}, duration=time.time() - start_time)
                    
                    st.rerun()
                else:
                    main_app()
    else:        
        login_form()

if __name__ == "__main__":
    main()