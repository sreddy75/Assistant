import os
import re
import json
import streamlit as st
from collections import defaultdict
from src.backend.kr8.utils.log import logger
import pandas as pd
import io
import base64
from PIL import Image
from io import BytesIO
import plotly.graph_objects as go
import requests
from dotenv import load_dotenv
from src.backend.kr8.vectordb.pgvector.pgvector2 import PgVector2

load_dotenv()
BACKEND_URL=os.getenv("BACKEND_URL")

def logout():
    if 'token' in st.session_state:
        requests.post(f"{BACKEND_URL}/api/logout", headers={"Authorization": f"Bearer {st.session_state['token']}"})
    st.session_state.clear()

def sanitize_content(content):
    def format_code_block(match):
        lang = match.group(1) or ''
        code = match.group(2).strip()
        if lang.lower() == 'json':
            try:
                parsed = json.loads(code)
                code = json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                pass  # If it's not valid JSON, leave it as is
        return f"```{lang}\n{code}\n```"

    # Handle code blocks (with or without language specification)
    content = re.sub(r'```(\w*)\s*([\s\S]*?)```', format_code_block, content)

    # Handle inline code
    content = re.sub(r'`([^`\n]+)`', r'`\1`', content)

    # Handle headers
    content = re.sub(r'^(#+)\s*(.*?)$', lambda m: f'{m.group(1)} {m.group(2).strip()}', content, flags=re.MULTILINE)

    # Handle unordered lists
    content = re.sub(r'^(\s*[-*+])\s*(.*?)$', lambda m: f'{m.group(1)} {m.group(2).strip()}', content, flags=re.MULTILINE)

    # Handle ordered lists
    content = re.sub(r'^(\s*\d+\.)\s*(.*?)$', lambda m: f'{m.group(1)} {m.group(2).strip()}', content, flags=re.MULTILINE)

    # Handle bold and italic
    content = re.sub(r'\*\*(.*?)\*\*', r'**\1**', content)
    content = re.sub(r'\*(.*?)\*', r'*\1*', content)

    # Handle links
    content = re.sub(r'\[(.*?)\]\((.*?)\)', r'[\1](\2)', content)

    # Handle horizontal rules
    content = re.sub(r'^(-{3,}|\*{3,}|_{3,})$', '---', content, flags=re.MULTILINE)

    # Replace common escape sequences
    content = content.replace('&quot;', '"').replace('&apos;', "'").replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')

    # Replace escaped newlines with actual newlines
    content = content.replace('\\n', '\n')

    # Remove extra whitespace
    content = re.sub(r'\n\s*\n', '\n\n', content)
    
    # Ensure consistent newlines before and after code blocks
    content = re.sub(r'([\s\S]+?)(```[\s\S]+?```)', lambda m: f"{m.group(1).strip()}\n\n{m.group(2)}\n\n", content)
    
    # Ensure consistent formatting for bullet points
    content = re.sub(r'^\* \*([^:]+):\*\*', r'* **\1:**', content, flags=re.MULTILINE)

    # Ensure consistent newlines after headers
    content = re.sub(r'(#+.*?)\n(?!\n)', r'\1\n\n', content)

    content = content.strip()

    return content

def render_markdown(content):
    # Function to replace markdown code blocks with st.code()
    def replace_code_block(match):
        language = match.group(1) or ""
        code = match.group(2)
        return f"$CODE_BLOCK${language}${code}$CODE_BLOCK$"

    # Replace code blocks with placeholders
    content = re.sub(r'```(\w*)\n([\s\S]*?)```', replace_code_block, content)

    # Split content by code block placeholders
    parts = content.split('$CODE_BLOCK$')

    st.markdown('<div class="chat-message assistant-response">', unsafe_allow_html=True)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Render non-code parts as markdown
            st.markdown(part, unsafe_allow_html=True)
        else:
            # Render code parts
            language, code = part.split('$', 1)
            st.code(code, language=language if language else None)
    st.markdown('</div>', unsafe_allow_html=True)
    
def determine_analyst(file, file_content):
    # Read a sample of the file to determine its content
    if file.name.endswith('.csv'):
        df = pd.read_csv(io.StringIO(file_content), nrows=5)
    elif file.name.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(io.BytesIO(base64.b64decode(file_content)), nrows=5)
    else:
        return None

    # Check column names for keywords
    columns = df.columns.str.lower()
    if any(keyword in columns for keyword in ['revenue', 'financial', 'profit', 'cost']):
        return 'financial'
    else:
        return 'data'

def display_base64_image(base64_string):
    try:
        # Remove the "data:image/png;base64," part if present
        if "base64," in base64_string:
            base64_string = base64_string.split("base64,")[1]
        
        # Decode the base64 string
        img_data = base64.b64decode(base64_string)
        
        # Open the image using PIL
        img = Image.open(BytesIO(img_data))
        
        # Display the image using Streamlit
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