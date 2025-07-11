import os
import streamlit as st
import re
import json
import requests
import pandas as pd
import base64
from io import BytesIO
from PIL import Image
import plotly.graph_objects as go
from markdown_it import MarkdownIt
from bs4 import BeautifulSoup
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
import logging
from utils.api import BACKEND_URL
from dotenv import load_dotenv
load_dotenv()

def get_client_name():
    return os.getenv('CLIENT_NAME', 'default')

def setup_logging():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    return logger

logger = setup_logging()

def add_markdown_styles():
    markdown_style = """
    <style>
    /* Add your markdown styles here */
    </style>
    """
    st.markdown(markdown_style, unsafe_allow_html=True)

def safe_get(data, *keys, default=None):
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data

def format_metric(value, format_string="{:.2f}", suffix=""):
    if value is None:
        return "N/A"
    try:
        return f"{format_string.format(value)}{suffix}"
    except (ValueError, TypeError):
        return str(value) + suffix

def display_base64_image(base64_string):
    try:
        if "base64," in base64_string:
            base64_string = base64_string.split("base64,")[1]
        img_data = base64.b64decode(base64_string)
        img = Image.open(BytesIO(img_data))
        st.image(img, use_column_width=True)
    except Exception as e:
        st.error(f"Error displaying image: {e}")
        logger.error(f"Error displaying image: {str(e)}", exc_info=True)

def render_chart(chart_data):
    try:
        fig = go.Figure(data=chart_data['data']['data'], layout=chart_data['data']['layout'])
        st.plotly_chart(fig, use_container_width=True)
        if 'interpretation' in chart_data:
            st.write(chart_data['interpretation'])
    except Exception as e:
        st.error(f"Error rendering chart: {e}")
        logger.error(f"Error rendering chart: {str(e)}", exc_info=True)

def is_authenticated():
    if 'token' in st.session_state:
        response = requests.get(f"{BACKEND_URL}/api/v1/auth/is_authenticated", headers={"Authorization": f"Bearer {st.session_state['token']}"})
        return response.status_code == 200 and response.json().get('authenticated', False)
    return False

def restart_assistant():
    logger.debug("---*--- Restarting Assistant ---*---")
    st.session_state["llm_os"] = None
    st.session_state["llm_os_run_id"] = None
    if "url_scrape_key" in st.session_state:
        st.session_state["url_scrape_key"] += 1
    if "file_uploader_key" in st.session_state:
        st.session_state["file_uploader_key"] += 1
    st.rerun()

def handle_response(response, success_message=None):
    if response.status_code == 200:
        if success_message:
            st.success(success_message)
        return True
    elif response.status_code == 400:
        error_detail = json.loads(response.text).get('detail', 'Unknown error')
        if isinstance(error_detail, list):
            for error in error_detail:
                st.error(f"Error: {error.get('msg', 'Unknown error')}")
        else:
            st.error(f"Error: {error_detail}")
    elif response.status_code == 401:
        st.error("Authentication failed. Please log in again.")
    elif response.status_code == 404:
        st.error("Resource not found. Please check your input.")
    else:
        st.error(f"An error occurred: {response.text}")
    return False

def send_event(event_type, event_data, duration=None):
    try:
        user_id = st.session_state.get("user_id")        
        payload = {
            "user_id": user_id,            
            "event_type": event_type,
            "event_data": event_data,
            "duration": duration
        }
        response = requests.post(
            f"{BACKEND_URL}/api/v1/analytics/user-events",
            json=payload,
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if response.status_code != 200:
            logger.error(f"Failed to send event: {response.text}")
        else:
            logger.info(f"Event sent successfully: {event_type} for user {user_id}")
    except Exception as e:
        logger.error(f"Error sending event: {str(e)}")
        
def validate_email(email):
    """Validate email format."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength."""
    if len(password) < 8:
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True
        