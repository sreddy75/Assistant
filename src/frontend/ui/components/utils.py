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
from markdown import markdown
from bs4 import BeautifulSoup
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
    # Pre-process the content
    content = re.sub(r'\*\s*([^*]+)\s*\*:', r'**\1:**', content)  # Convert *Title*: to **Title:**
    content = re.sub(r'^\s*\*\s*', '- ', content, flags=re.MULTILINE)  # Convert * to -
    content = re.sub(r'^\s*(\d+)\.\s*\*\s*', r'\1. ', content, flags=re.MULTILINE)  # Remove * from numbered lists

    # Convert markdown to HTML
    html = markdown(content, extensions=['fenced_code', 'codehilite', 'tables'])
    
    # Parse the HTML
    soup = BeautifulSoup(html, 'html.parser')
    
    # Process code blocks
    for code_block in soup.find_all('pre'):
        code = code_block.find('code')
        if code:
            language = code.get('class', [''])[0].replace('language-', '')
            formatted_code = f'<pre><code class="language-{language}">{code.string}</code></pre>'
            code_block.replace_with(BeautifulSoup(formatted_code, 'html.parser'))
    
    # Wrap the content in a div for styling
    wrapped_content = f'<div class="markdown-content">{soup.prettify()}</div>'
    
    # Render the processed HTML
    st.markdown(wrapped_content, unsafe_allow_html=True)

def add_markdown_styles():
    markdown_style = """
    <style>
        .markdown-content {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #ffffff;
            max-width: 800px;  /* Limit the maximum width */
            margin: 0 auto;  /* Center the content */
        }
        .markdown-content h1, .markdown-content h2, .markdown-content h3, 
        .markdown-content h4, .markdown-content h5, .markdown-content h6 {
            color: #ffffff;
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }
        .markdown-content h1 { font-size: 2em; border-bottom: 1px solid #30363d; }
        .markdown-content h2 { font-size: 1.5em; border-bottom: 1px solid #30363d; }
        .markdown-content h3 { font-size: 1.25em; }
        .markdown-content h4 { font-size: 1em; }
        .markdown-content h5 { font-size: 0.875em; }
        .markdown-content h6 { font-size: 0.85em; color: #8b949e; }
        .markdown-content p, .markdown-content ul, .markdown-content ol {
            margin-bottom: 16px;
        }
        .markdown-content ul, .markdown-content ol {
            padding-left: 2em;
        }
        .markdown-content li {
            margin-bottom: 0.25em;
        }
        .markdown-content code {
            font-family: 'Courier New', Courier, monospace;
            padding: 0.2em 0.4em;
            margin: 0;
            font-size: 85%;
            background-color: rgba(110, 118, 129, 0.4);
            border-radius: 6px;
        }
        .markdown-content pre {
            padding: 16px;
            overflow: auto;
            font-size: 85%;
            line-height: 1.45;
            background-color: #161b22;
            border-radius: 6px;
        }
        .markdown-content pre code {
            background-color: transparent;
            padding: 0;
            margin: 0;
            font-size: 100%;
            word-break: normal;
            white-space: pre;
            background: transparent;
            border: 0;
        }
    </style>
    """
    st.markdown(markdown_style, unsafe_allow_html=True)
    
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