import streamlit as st
import toml
from utils.auth import is_authenticated, login_form, logout
from styles.custom_theme import load_theme_config, apply_custom_theme, maximize_content_area, apply_expander_style
from views.home_page import render_home_page
from views.chat_page import render_chat_page
from views.knowledge_base_page import render_knowledge_base_page
from views.analytics_page import render_analytics_page
from views.settings_page import render_settings_page
from components.sidebar_manager import render_sidebar
from utils.helpers import setup_logging, get_client_name
from utils.api import BACKEND_URL
import datetime
import requests

@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_load_org_config():
    return load_org_config()

def load_org_config():
    """
    Load the organization configuration from the server.
    Returns the org config as a dictionary if successful, an empty dict otherwise.
    """
    client_name = get_client_name()
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/organizations/public-config/{client_name}")
        response.raise_for_status()
        # Parse the TOML content
        config = toml.loads(response.text)
        return config
    except requests.RequestException as e:
        st.warning(f"Failed to load organization configuration: {str(e)}")
        return {}
    except toml.TomlDecodeError as e:
        st.warning(f"Failed to parse organization configuration: {str(e)}")
        return {}
    
def main():
    setup_logging()
    
    # Load theme configuration
    theme_config = load_theme_config()
    
    # Apply theme (will use default values if theme_config is None)
    apply_custom_theme(theme_config)
    maximize_content_area()
    apply_expander_style()
    
    render_layout()
    
    if not is_authenticated():
        login_form()
    else:
        # Load organization config after authentication
        org_config = load_org_config()
        render_main_app()
        
def render_layout():
    current_year = datetime.datetime.now().year
    layout = f"""
    <style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    .stApp {{ 
        display: flex;
        flex-direction: column;
        min-height: 100vh;
    }}
    .main-content {{
        flex: 1 0 auto;
        padding-bottom: 40px;  /* Height of the footer */
        width: 100%;
        max-width: 100%;
    }}
    .footer {{
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        height: 30px;
        line-height: 30px;
        background-color: #979ca6;
        text-align: center;
        color: #080606;
        font-size: 12px;
        border-top: 1px solid #e5e5e5;
        z-index: 999;
    }}
    .stApp > header {{
        z-index: 1000;
    }}
    .stApp > .withScreencast {{
        z-index: 1000;
    }}
    </style>

    <div class="main-content">
    """
    st.markdown(layout, unsafe_allow_html=True)

def render_footer():
    current_year = datetime.datetime.now().year
    footer = f"""
    </div>
    <div class="footer">
        © {current_year} KR8 IT PTY LTD. All rights reserved.
    </div>
    """
    st.markdown(footer, unsafe_allow_html=True)

def render_main_app():
    # Initialize session state for navigation
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"

    # Load cached org config
    org_config = cached_load_org_config()

    # Navigation using tabs
    tabs = st.tabs(["Dashboard", "Chat", "Knowledge Base", "Analytics", "Settings"])
    
    render_sidebar()
    
    with tabs[0]:
        st.session_state.current_page = "Dashboard"
        render_home_page(org_config)
    
    with tabs[1]:
        st.session_state.current_page = "Chat"
        render_chat_page()
    
    with tabs[2]:
        st.session_state.current_page = "Knowledge Base"
        render_knowledge_base_page()
    
    with tabs[3]:
        st.session_state.current_page = "Analytics"
        if st.session_state.get('is_admin', False):
            render_analytics_page()
        else:
            st.error("You don't have permission to access this page.")
    
    with tabs[4]:
        st.session_state.current_page = "Settings"
        if st.session_state.get('is_super_admin', False):
            render_settings_page()
        else:
            st.error("You don't have permission to access this page.")

    # Logout button
    if st.sidebar.button("Logout", key="logout_button"):        
        logout()
        st.rerun()
        
if __name__ == "__main__":
    main()

# Add this at the very end of your script
render_footer()