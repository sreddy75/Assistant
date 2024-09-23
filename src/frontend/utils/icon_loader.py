import streamlit as st
import requests
from PIL import Image
from io import BytesIO
import logging
from utils.api import BACKEND_URL

logger = logging.getLogger(__name__)

@st.cache_data(ttl=3600)
def load_org_icons():
    org_id = st.session_state.get('org_id')
    if not org_id:
        logger.warning("Organization ID not found in session state")
        return None, None

    system_chat_icon = user_chat_icon = None
    try:
        system_icon_response = requests.get(
            f"{BACKEND_URL}/api/v1/organizations/asset/{org_id}/chat_system_icon",
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if system_icon_response.status_code == 200:
            system_chat_icon = Image.open(BytesIO(system_icon_response.content))

        user_icon_response = requests.get(
            f"{BACKEND_URL}/api/v1/organizations/asset/{org_id}/chat_user_icon",
            headers={"Authorization": f"Bearer {st.session_state.get('token')}"}
        )
        if user_icon_response.status_code == 200:
            user_chat_icon = Image.open(BytesIO(user_icon_response.content))
    except Exception as e:
        logger.error(f"Error loading organization icons: {str(e)}")

    return system_chat_icon, user_chat_icon