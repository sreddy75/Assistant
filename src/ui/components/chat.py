import base64
import io
import random
import re, html
from sqlite3 import IntegrityError
import time
from collections import defaultdict
import traceback
from typing import Optional
import requests
import pandas as pd
import streamlit as st
from service.tuning import SessionLocal, adjust_response_based_on_feedback, analyze_feedback_text, get_sentiment_analysis, get_vote_analysis, plot_sentiment_analysis
from utils.auth import BACKEND_URL
from kr8.utils.log import logger
from assistant import get_llm_os
from kr8.document.reader.website import WebsiteReader
from kr8.document.reader.pdf import PDFReader
from multiprocessing import Pool
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import asyncio
from kr8.document import Document
from PIL import Image
from plotly.subplots import make_subplots
import json
import streamlit as st
import plotly.graph_objects as go
from transformers import GPT2Tokenizer
import json
import base64
from io import BytesIO
from kr8.vectordb.pgvector import PgVector2
from PIL import Image
import os
from dotenv import load_dotenv
import json
from config.client_config import is_feedback_sentiment_analysis_enabled
from team.data_analyst import EnhancedDataAnalyst
from team.financial_analyst import EnhancedFinancialAnalyst
from service.analytics_service import analytics_service

# Load environment variables
load_dotenv()

# Initialize the tokenizer
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

MAX_TOKENS = 4096  # Adjust based on the model 
BUFFER_TOKENS = 1000  # some room for the response

client_name = os.getenv('CLIENT_NAME', 'default')

# Load the custom icons
meerkat_icon = Image.open(f"src/config/themes/{client_name}/chat_system_icon.png")
user_icon = Image.open(f"src/config/themes/{client_name}/chat_user_icon.png")
llm_os = None

def count_tokens(text):
    return len(tokenizer.encode(text))

def truncate_conversation(messages, max_tokens):
    total_tokens = 0
    truncated_messages = []
    for message in reversed(messages):
        message_tokens = count_tokens(message['content'])
        if total_tokens + message_tokens > max_tokens:
            break
        total_tokens += message_tokens
        truncated_messages.insert(0, message)
    return truncated_messages

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


import plotly.graph_objects as go
import json
import logging
def render_chart(chart_data):
    try:
        fig = go.Figure(data=chart_data['data']['data'], layout=chart_data['data']['layout'])
        st.plotly_chart(fig, use_container_width=True)
        if 'interpretation' in chart_data:
            st.write(chart_data['interpretation'])
    except Exception as e:
        st.error(f"Error rendering chart: {e}")
        logger.error(f"Error rendering chart: {str(e)}", exc_info=True)
                        
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
            
def render_chat(user_id: Optional[int] = None, user_role: Optional[str] = None):
    st.markdown("""
        <style>
        .chat-message, .chat-message p, .chat-message li, .chat-message h1, .chat-message h2, .chat-message h3, .chat-message h4, .chat-message h5, .chat-message h6 {
            color: white !important;
        }
        .assistant-response, .assistant-response p, .assistant-response li, .assistant-response h1, .assistant-response h2, .assistant-response h3, .assistant-response h4, .assistant-response h5, .assistant-response h6 {
            color: white !important;
        }
        .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
    st.markdown("""
        <style>
        @keyframes pulse {
            0% { transform: scale(0.8); opacity: 0.7; }
            50% { transform: scale(1); opacity: 1; }
            100% { transform: scale(0.8); opacity: 0.7; }
        }
        .pulsating-dot {
            width: 20px; height: 20px;
            background-color: #ff0000;
            border-radius: 50%;
            display: inline-block;
            animation: pulse 1.5s ease-in-out infinite;
        }
        </style>
        """, unsafe_allow_html=True)

    if "llm_id" not in st.session_state:
        st.session_state.llm_id = "gpt-4o"
        logger.warning("llm_id not found in session state, using default value")

    llm_id = st.session_state.llm_id
    llm_os = initialize_assistant(llm_id, user_id)

    if llm_os is None:
        st.warning("The assistant is currently unavailable. Please try again later.")
        return
        
    try:
        st.session_state["llm_os_run_id"] = llm_os.create_run()
    except Exception:
        st.warning("Could not create LLM OS run, is the database running?")
        return

    assistant_chat_history = llm_os.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Ask me questions..."}]

    chat_container = st.container()

    with chat_container:
        for i, message in enumerate(st.session_state["messages"]):
            if message["role"] == "assistant":
                with st.chat_message(message["role"], avatar=meerkat_icon):
                    sanitized_content = sanitize_content(message["content"])
                    render_markdown(sanitized_content)
                    
                    query = st.session_state["messages"][i-1]["content"] if i > 0 else ""
                    
                    with st.expander("Provide feedback", expanded=True):
                        if is_feedback_sentiment_analysis_enabled():
                            usefulness = st.slider("How useful was this response?", 1, 5, 3, key=f"usefulness_{i}")
                            feedback = st.text_area("Additional feedback (optional)", key=f"feedback_text_{i}")
                            if st.button("Submit Feedback", key=f"feedback_button_{i}"):
                                submit_feedback(user_id, query, sanitized_content, usefulness > 3, usefulness, feedback)
                        else:
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("👍", key=f"upvote_{i}"):
                                    submit_simple_vote(user_id, query, sanitized_content, True)
                            with col2:
                                if st.button("👎", key=f"downvote_{i}"):
                                    submit_simple_vote(user_id, query, sanitized_content, False)
                                
            elif message["role"] == "user":
                with st.chat_message(message["role"], avatar=user_icon):
                    sanitized_content = sanitize_content(message["content"])
                    render_markdown(sanitized_content)

    if prompt := st.chat_input("What would you like to know?"):
        st.session_state["messages"].append({"role": "user", "content": prompt})
        
        truncated_messages = truncate_conversation(st.session_state["messages"], MAX_TOKENS - BUFFER_TOKENS)
        
        start_time = time.time()
        
        analytics_service.log_event(user_id, "user_query", {"query": prompt})
        
        with chat_container:
            with st.chat_message("user", avatar=user_icon):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar=meerkat_icon):
                response_area = st.container()
                
                with response_area:
                    pulsating_dot = st.empty()
                    pulsating_dot.markdown('<div class="pulsating-dot"></div>', unsafe_allow_html=True)
                    response_placeholder = st.empty()

                used_tools = []
                used_assistants = []

                try:
                    current_project = st.session_state.get('current_project')
                    current_project_type = st.session_state.get('current_project_type')
                    context_prompt = f"In the context of the {current_project_type} project '{current_project}': {prompt}" if current_project and current_project_type else prompt

                    full_response = ""
                    for chunk in llm_os.run(context_prompt, messages=truncated_messages, stream=True):
                        full_response += chunk
                        with response_area:
                            pulsating_dot.markdown('<div class="pulsating-dot"></div>', unsafe_allow_html=True)
                            response_placeholder.markdown(sanitize_content(full_response) + "▌")
                        time.sleep(0.01)

                    sanitized_response = sanitize_content(full_response)
                    
                    # Use feedback-adjusted response
                    with SessionLocal() as db:
                        adjusted_response = adjust_response_based_on_feedback(sanitized_response, prompt, db)
                    
                    with response_area:
                        pulsating_dot.empty()
                        response_placeholder.markdown(
                            f'<div class="chat-message">{adjusted_response}</div>',
                            unsafe_allow_html=True
                        )
                    
                    process_response_content(adjusted_response)

                    st.session_state["messages"].append({"role": "assistant", "content": adjusted_response})

                    with st.expander("Provide feedback", expanded=True):
                        if is_feedback_sentiment_analysis_enabled():
                            usefulness = st.slider("How useful was this response?", 1, 5, 3, key=f"usefulness_{len(st.session_state['messages'])-1}")
                            feedback = st.text_area("Additional feedback (optional)", key=f"feedback_text_{len(st.session_state['messages'])-1}")
                            if st.button("Submit Feedback", key=f"feedback_button_{len(st.session_state['messages'])-1}"):
                                submit_feedback(user_id, prompt, adjusted_response, usefulness > 3, usefulness, feedback)
                        else:
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("👍", key=f"upvote_{len(st.session_state['messages'])-1}"):
                                    submit_simple_vote(user_id, prompt, adjusted_response, True)
                            with col2:
                                if st.button("👎", key=f"downvote_{len(st.session_state['messages'])-1}"):
                                    submit_simple_vote(user_id, prompt, adjusted_response, False)

                except Exception as e:
                    with response_area:
                        pulsating_dot.empty()
                        st.error(f"An unexpected error occurred: {str(e)}")
                    logger.error(f"Unexpected error: {str(e)}")
                    full_response = "I apologize, but I encountered an error while processing your request. Please try again."
                    response_placeholder.markdown(full_response)

        response_time = time.time() - start_time
        analytics_service.log_event(user_id, "assistant_response", {
            "response_length": len(full_response),
            "tools_used": used_tools,
            "assistants_used": used_assistants
        }, duration=response_time)
        
    if llm_os.knowledge_base:
        manage_knowledge_base(llm_os)

def submit_feedback(user_id: int, query: str, response: str, is_upvote: bool, usefulness_rating: int, feedback_text: str):
    headers = {"Authorization": f"Bearer {st.session_state.get('token', '')}"}
    response = requests.post(
        f"{BACKEND_URL}/submit-feedback",
        json={
            "user_id": user_id,
            "query": query,
            "response": response,
            "is_upvote": is_upvote,
            "usefulness_rating": usefulness_rating,
            "feedback_text": feedback_text
        },
        headers=headers
    )
    if response.status_code == 200:
        st.success("Feedback submitted successfully!")
    elif response.status_code == 401:
        st.error("Authentication failed. Please log in again.")
        # Optionally, clear the token and redirect to login
        st.session_state.token = None
        st.experimental_rerun()
    else:
        st.error(f"Failed to submit feedback. Status code: {response.status_code}")

def submit_simple_vote(user_id: int, query: str, response: str, is_upvote: bool):
    response = requests.post(
        f"{BACKEND_URL}/submit-vote",
        json={
            "user_id": user_id,
            "query": query,
            "response": response,
            "is_upvote": is_upvote
        },
        headers={"Authorization": f"Bearer {st.session_state['token']}"}
    )
    if response.status_code == 200:
        st.success("Vote submitted successfully!")
    else:
        st.error("Failed to submit vote. Please try again.")
        
def process_response_content(sanitized_response):
    # Find and render any JSON structures that might be charts
    json_pattern = re.compile(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}')
    json_matches = json_pattern.findall(sanitized_response)
    for json_str in json_matches:
        try:
            chart_data = json.loads(json_str)
            if 'chart_type' in chart_data and 'data' in chart_data:
                render_chart(chart_data)
        except json.JSONDecodeError:
            pass  # Not a valid JSON, skip it

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
            
from typing import Dict
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import traceback

def render_analytics_dashboard():
    st.header("Analytics Dashboard")

    sentiment_analysis = get_sentiment_analysis()
    feedback_analysis = analyze_feedback_text()
    
    print("Sentiment Analysis Result:", sentiment_analysis)
    print("Feedback Analysis Result:", feedback_analysis)
    
    if "error" in sentiment_analysis:
        st.warning(f"No vote data available: {sentiment_analysis['error']}")
        st.info("The analytics dashboard will populate with data once users start providing feedback.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            if 'average_sentiment_score' in sentiment_analysis:
                st.metric("Average Sentiment Score", f"{sentiment_analysis['average_sentiment_score']:.2f}")
        with col2:
            if 'average_usefulness_rating' in sentiment_analysis:
                st.metric("Average Usefulness Rating", f"{sentiment_analysis['average_usefulness_rating']:.2f}")
        with col3:
            if 'upvote_percentage' in sentiment_analysis:
                st.metric("Upvote Percentage", f"{sentiment_analysis['upvote_percentage']:.2f}%")
    
    try:
        fig = plot_sentiment_analysis(sentiment_analysis)
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Error plotting sentiment analysis: {str(e)}")
        print(f"Error details: {traceback.format_exc()}")
    
    st.subheader("Feedback Analysis")
    if feedback_analysis and feedback_analysis.get("feedback_count", 0) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("Top 10 Words")
            word_freq = pd.DataFrame(list(feedback_analysis['word_frequency'].items()), columns=['Word', 'Frequency'])
            word_freq = word_freq.sort_values('Frequency', ascending=False).head(10)
            fig = px.bar(word_freq, x='Word', y='Frequency', title="Most Frequent Words in Feedback")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.write("Sentiment Distribution")
            sentiment_dist = pd.DataFrame(list(feedback_analysis['sentiment_distribution'].items()), columns=['Sentiment', 'Percentage'])
            fig = px.pie(sentiment_dist, values='Percentage', names='Sentiment', title="Sentiment Distribution")
            st.plotly_chart(fig, use_container_width=True)
        
        st.write(f"Average Sentiment: {feedback_analysis['average_sentiment']:.2f}")
        st.write(f"Sentiment-Usefulness Correlation: {feedback_analysis['sentiment_usefulness_correlation']:.2f}")
        
        st.subheader("Main Topics")
        for topic in feedback_analysis['topics']:
            st.write(topic)
        
        st.subheader("Top Keywords")
        keywords = pd.DataFrame(list(feedback_analysis['top_keywords'].items()), columns=['Keyword', 'Score'])
        keywords = keywords.sort_values('Score', ascending=False).head(10)
        fig = px.bar(keywords, x='Keyword', y='Score', title="Top Keywords in Feedback")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No feedback text available for analysis yet. This section will update as users provide feedback.")

    # Overview metrics
    total_users = analytics_service.get_unique_users()
    event_summary = analytics_service.get_event_summary()

    st.header("Usage Analytics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Users", total_users)
    with col2:
        total_queries = event_summary.get('user_query', 0)
        st.metric("Total Queries", total_queries)
    with col3:
        total_responses = event_summary.get('assistant_response', 0)
        st.metric("Total Responses", total_responses)
    
    st.markdown('<hr class="dark-divider">', unsafe_allow_html=True)           
    
    st.subheader("Most Used Tools")
    most_used_tools = analytics_service.get_most_used_tools()
    if most_used_tools:
        tools_df = pd.DataFrame(most_used_tools, columns=['Tool', 'Usage Count'])
        fig = px.bar(tools_df, x='Tool', y='Usage Count', title='Most Used Tools')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No tool usage data available yet.")
        
    st.markdown('<hr class="dark-divider">', unsafe_allow_html=True)           
    
    # Event Summary as a horizontal bar chart
    st.subheader("Event Summary")
    if event_summary:
        event_df = pd.DataFrame(list(event_summary.items()), columns=['Event', 'Count'])
        fig = px.bar(event_df, x='Count', y='Event', orientation='h')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No event summary data available yet.")

    st.markdown('<hr class="dark-divider">', unsafe_allow_html=True)           
    
    # User activity over time
    st.subheader("User Activity Over Time")
    all_events = analytics_service.get_user_events()
    if all_events:
        activity_data = [{"date": event['timestamp'].date(), "count": 1} for event in all_events]
        activity_df = pd.DataFrame(activity_data)
        activity_df = activity_df.groupby('date').sum().reset_index()
        
        # Use a line chart with markers for better visibility
        fig = px.line(activity_df, x='date', y='count', markers=True, title='Daily User Activity')
        fig.update_layout(xaxis_title='Date', yaxis_title='Number of Events')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No user activity data available yet.")

    st.markdown('<hr class="dark-divider">', unsafe_allow_html=True)           
    
    # User-specific analytics
    st.subheader("User Analytics")
    user_id = st.selectbox("Select User", options=[None] + list(range(1, total_users + 1)))
    
    if user_id:
        events = analytics_service.get_user_events(user_id)
        
        if events:
            # User activity heatmap
            st.subheader(f"Activity Heatmap for User {user_id}")
            activity_data = [{"date": event['timestamp'].date(), "hour": event['timestamp'].hour, "count": 1} for event in events]
            activity_df = pd.DataFrame(activity_data)
            activity_df = activity_df.groupby(['date', 'hour']).sum().reset_index()
            
            # Create a pivot table for the heatmap
            pivot_df = activity_df.pivot(index='date', columns='hour', values='count').fillna(0)
            
            fig = go.Figure(data=go.Heatmap(
                z=pivot_df.values,
                x=pivot_df.columns,
                y=pivot_df.index,
                colorscale='Viridis'))
            
            fig.update_layout(
                title='User Activity Heatmap',
                xaxis_title='Hour of Day',
                yaxis_title='Date'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Most used tools and assistants
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Most Used Tools")
                tool_usage = {}
                for event in events:
                    if event['event_type'] == 'assistant_response':
                        for tool in event['event_data'].get('tools_used', []):
                            tool_usage[tool] = tool_usage.get(tool, 0) + 1
                
                if tool_usage:
                    tool_df = pd.DataFrame(list(tool_usage.items()), columns=['Tool', 'Usage'])
                    fig = px.pie(tool_df, values='Usage', names='Tool', title='Tool Usage Distribution')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No tool usage data available for this user.")
            
            with col2:
                st.subheader("Most Used Assistants")
                assistant_usage = {}
                for event in events:
                    if event['event_type'] == 'assistant_response':
                        for assistant in event['event_data'].get('assistants_used', []):
                            assistant_usage[assistant] = assistant_usage.get(assistant, 0) + 1
                
                if assistant_usage:
                    assistant_df = pd.DataFrame(list(assistant_usage.items()), columns=['Assistant', 'Usage'])
                    fig = px.pie(assistant_df, values='Usage', names='Assistant', title='Assistant Usage Distribution')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No assistant usage data available for this user.")
            
            # Average response time over time
            st.subheader("Average Response Time Trend")
            response_times = [
                {"timestamp": event['timestamp'], "duration": event['duration']}
                for event in events
                if event['event_type'] == 'assistant_response' and event['duration']
            ]
            if response_times:
                response_df = pd.DataFrame(response_times)
                response_df['date'] = response_df['timestamp'].dt.date
                daily_avg = response_df.groupby('date')['duration'].mean().reset_index()
                
                fig = px.line(daily_avg, x='date', y='duration', title='Daily Average Response Time')
                fig.update_layout(xaxis_title='Date', yaxis_title='Average Response Time (seconds)')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No response time data available for this user.")
        else:
            st.info(f"No activity data available for User {user_id}.")

    # Recent global activity
    st.subheader("Recent Global Activity")
    recent_events = analytics_service.get_user_events()[:50]  # Get last 50 events
    
    if recent_events:
        # Create a DataFrame for recent events
        recent_df = pd.DataFrame([
            {
                "User ID": event['user_id'],
                "Timestamp": event['timestamp'],
                "Event Type": event['event_type']
            }
            for event in recent_events
        ])
        
        # Display recent events as an interactive table
        st.dataframe(recent_df, use_container_width=True)

        # Add a download button for the full activity log
        csv = recent_df.to_csv(index=False)
        st.download_button(
            label="Download Full Activity Log",
            data=csv,
            file_name="activity_log.csv",
            mime="text/csv",
        )
    else:
        st.info("No recent activity data available.")
                
def initialize_assistant(llm_id, user_id=None):
    if "llm_os" not in st.session_state or st.session_state["llm_os"] is None:
        logger.info(f"---*--- Creating {llm_id} LLM OS ---*---")
        
        user_nickname = st.session_state.get("nickname", "friend")
        user_role = st.session_state.get("role", "default")

        try:
            llm_os = get_llm_os(
                llm_id=llm_id,
                user_id=user_id,
                user_role=user_role,
                user_nickname=user_nickname,
                run_id=st.session_state.get("run_id"),
                debug_mode=st.session_state.get("debug_mode", False),
                web_search=st.session_state.get("web_search_enabled", True)
            )
            st.session_state["llm_os"] = llm_os
            logger.info(f"Initialized LLM OS with team: {[assistant.name for assistant in llm_os.team]}")
            
            data_analyst = next((a for a in llm_os.team if isinstance(a, EnhancedDataAnalyst)), None)
            if data_analyst:
                logger.info(f"EnhancedDataAnalyst initialized with pandas_tools: {data_analyst.pandas_tools is not None}")
            else:
                logger.warning("EnhancedDataAnalyst not found in the team")
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM OS: {str(e)}", exc_info=True)
            st.error(f"An error occurred while initializing the assistant: {str(e)}")
            return None        
    else:
        llm_os = st.session_state["llm_os"]
        logger.info(f"Using existing LLM OS with team: {[assistant.name for assistant in llm_os.team]}")

    return llm_os

def chunk_pdf(pdf_content, chunk_size=1000):
    words = pdf_content.split()
    for i in range(0, len(words), chunk_size):
        yield ' '.join(words[i:i+chunk_size])

async def process_pdf_async(uploaded_file, llm_os):
    reader = PDFReader()
    auto_rag_documents = reader.read(uploaded_file)
    if not auto_rag_documents:
        logger.error(f"Could not read PDF: {uploaded_file.name}")
        return False, f"Could not read PDF: {uploaded_file.name}"
    
    logger.info(f"Successfully read PDF: {uploaded_file.name}. Found {len(auto_rag_documents)} documents.")
    
    total_chunks = len(auto_rag_documents)
    logger.info(f"Processing {uploaded_file.name} with {total_chunks} chunks.")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    start_time = time.time()
    
    documents_to_load = []
    for i, doc in enumerate(auto_rag_documents):
        status_text.text(f"Processing chunk {i+1} of {total_chunks}")
        try:
            doc.meta_data.update({"source": uploaded_file.name, "chunk_number": i+1, "user_id": llm_os.user_id})
            documents_to_load.append(doc)
            
            logger.info(f"Prepared chunk {i+1} of {total_chunks} for knowledge base.")
        except Exception as e:
            logger.error(f"Error preparing chunk {i+1} for knowledge base: {str(e)}")
        progress = (i + 1) / total_chunks
        progress_bar.progress(progress)
        
        time_elapsed = time.time() - start_time
        time_per_chunk = time_elapsed / (i + 1)
        eta = time_per_chunk * (total_chunks - i - 1)
        status_text.text(f"Processing chunk {i+1} of {total_chunks}. ETA: {eta:.2f} seconds")
    
    try:
        await asyncio.to_thread(llm_os.knowledge_base.load_documents, documents_to_load, upsert=True)
        logger.info(f"Successfully added all chunks to knowledge base.")
    except Exception as e:
        logger.error(f"Error adding chunks to knowledge base: {str(e)}")
    
    logger.info(f"Finished processing {uploaded_file.name}. Total time: {time.time() - start_time:.2f} seconds.")
    return True, f"Successfully processed {uploaded_file.name}"


def process_pdfs_parallel(uploaded_files, llm_os):
    with Pool() as pool:
        results = pool.starmap(PDFReader().read, [(file,) for file in uploaded_files])
    all_documents = [doc for result in results for doc in result]
    llm_os.knowledge_base.load_documents(all_documents, upsert=True)
    return True, f"Successfully processed {len(uploaded_files)} files"

def manage_knowledge_base(llm_os):
    
    if "loaded_dataframes" not in st.session_state:
        st.session_state["loaded_dataframes"] = {}
        
    if "processed_files" not in st.session_state:
        st.session_state["processed_files"] = []

    if "url_scrape_key" not in st.session_state:
        st.session_state["url_scrape_key"] = 0

    input_url = st.sidebar.text_input("Add URL to Knowledge Base", type="default", key=st.session_state["url_scrape_key"])
    add_url_button = st.sidebar.button("Add URL")
    if add_url_button:
        if input_url is not None:
            with st.spinner("Processing URLs..."):
                if f"{input_url}_scraped" not in st.session_state:
                    scraper = WebsiteReader(max_links=2, max_depth=1)
                    web_documents = scraper.read(input_url)
                    if web_documents:
                        llm_os.knowledge_base.load_documents(web_documents, upsert=True)
                        st.session_state[f"{input_url}_scraped"] = True
                        st.session_state["processed_files"].append(input_url)
                        st.session_state["user_documents"] = get_user_documents(llm_os.user_id)
                        st.sidebar.success(f"Successfully processed and added: {input_url}")
                        logger.info(f"Successfully processed and added URL: {input_url}")
                    else:
                        st.sidebar.error("Could not read website")
                        logger.error(f"Could not read website: {input_url}")

    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 100

    uploaded_files = st.sidebar.file_uploader(
        "Upload Documents", type=["pdf", "json", "csv", "xlsx", "xls", "zip"], key=st.session_state["file_uploader_key"], accept_multiple_files=True
    )

    if uploaded_files:
        financial_analyst = next((assistant for assistant in llm_os.team if assistant.name == "Enhanced Financial Analyst"), None)
        data_analyst = next((assistant for assistant in llm_os.team if assistant.name == "Enhanced Data Analyst"), None)
        
        for file in uploaded_files:
            with st.spinner(f"Processing {file.name}..."):
                try:                    
                    if file.name.endswith('.pdf'):
                        success, message = process_pdf(file, llm_os)
                        if success:
                            st.success(message)
                            st.session_state["processed_files"].append(file.name)
                            st.session_state["user_documents"] = get_user_documents(llm_os.user_id)
                        else:
                            st.error(message)
                    elif file.name.endswith(('.csv', '.xlsx', '.xls')):
                        file_content = base64.b64encode(file.read()).decode('utf-8')
                        analyst_type = determine_analyst(file, file_content)
                        
                        if analyst_type == 'financial' and financial_analyst:
                            result = process_file_for_analyst(llm_os, file, file_content, financial_analyst)                            
                        elif data_analyst:
                            result = process_file_for_analyst(llm_os, file, file_content, data_analyst)
                        else:
                            result = "Error: No data analyst available to process this file"

                        if result.startswith("Error:"):
                            st.error(result)
                        else:
                            st.success(f"Loaded {file.name}: {result}")
                            st.session_state["loaded_dataframes"][result] = {
                                "file_name": file.name,
                                "analyst_type": analyst_type
                            }
                            st.session_state["processed_files"].append(file.name)
                            st.session_state["user_documents"] = get_user_documents(llm_os.user_id)
                except Exception as e:
                    st.error(f"Error processing {file.name}: {str(e)}")
                    logger.error(f"Error processing {file.name}: {str(e)}")
                                        
        # Increment the file uploader key to force a refresh
        st.session_state["file_uploader_key"] += 1

    if st.session_state["processed_files"]:
        st.sidebar.markdown("### You are chatting with these files:")
        for file in st.session_state["processed_files"]:
            st.sidebar.write(file)

    if llm_os.knowledge_base and llm_os.knowledge_base.vector_db:
        if st.sidebar.button("Clear Knowledge Base"):
            llm_os.knowledge_base.vector_db.clear()
            st.session_state["processed_files"] = []
            st.sidebar.success("Knowledge base cleared")
            logger.info("Knowledge base cleared")

    # Add a button to list available dataframes
    # if st.sidebar.button("List Available Dataframes"):
    #     list_available_dataframes(llm_os)

    # # Add the debug button here
    # debug_knowledge_base(llm_os)
    
    if llm_os.team and len(llm_os.team) > 0:
        for team_member in llm_os.team:
            if len(team_member.memory.chat_history) > 0:
                with st.expander(f"{team_member.name} Memory", expanded=False):
                    st.container().json(team_member.memory.get_llm_messages())

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
    
def process_pdf(file, llm_os):
    reader = PDFReader()
    auto_rag_documents = reader.read(file)
    if not auto_rag_documents:
        logger.error(f"Could not read PDF: {file.name}")
        return False, f"Could not read PDF: {file.name}"
    
    logger.info(f"Successfully read PDF: {file.name}. Found {len(auto_rag_documents)} documents.")
    
    try:
        llm_os.knowledge_base.load_documents(auto_rag_documents)
        logger.info(f"Successfully added PDF content to knowledge base.")
        return True, f"Successfully processed {file.name}"
    except Exception as e:
        logger.error(f"Error adding PDF content to knowledge base: {str(e)}")
        return False, f"Error processing {file.name}: {str(e)}"

def process_file_for_analyst(llm_os, file, file_content, analyst):
    if analyst is None:
        logger.error(f"Analyst is None when processing file: {file.name}")
        return f"Error: Unable to process {file.name} due to missing analyst"

    if not hasattr(analyst, 'get_pandas_tools') or not callable(getattr(analyst, 'get_pandas_tools')):
        logger.error(f"Analyst {analyst.name if hasattr(analyst, 'name') else 'Unknown'} has no 'get_pandas_tools' method")
        return f"Error: Unable to process {file.name} due to misconfigured analyst"

    pandas_tools = analyst.get_pandas_tools()
    if not pandas_tools:
        logger.error(f"PandasTools not available for {analyst.name if hasattr(analyst, 'name') else 'Unknown'}")
        return f"Error: Unable to process {file.name} due to missing PandasTools"
    
    try:
        if file.name.endswith('.csv'):
            df_name = pandas_tools.load_csv(file.name, file_content)
            df = pandas_tools.dataframes[df_name]

            # Convert DataFrame to Document and store in vector database
            doc = Document(
                name=file.name,
                content=df.to_csv(index=False),
                meta_data={"type": "csv", "shape": df.shape}
            )
            # Use upsert operation to handle existing documents
            try:
                llm_os.knowledge_base.vector_db.upsert([doc])
                logger.info(f"Upserted CSV file {file.name} to vector database")
            except AttributeError:
                # If upsert is not available, fall back to insert
                try:
                    llm_os.knowledge_base.vector_db.insert([doc])
                    logger.info(f"Inserted CSV file {file.name} to vector database")
                except IntegrityError:
                    logger.warning(f"Document {file.name} already exists in the database. Skipping insertion.")
            
        elif file.name.endswith(('.xlsx', '.xls')):
            df_name = pandas_tools.load_excel(file.name, file_content)
        else:
            logger.error(f"Unsupported file type: {file.name}")
            return f"Error: Unsupported file type for {file.name}"
        
        logger.info(f"Successfully loaded {file.name} as {df_name}")
        return df_name
    except Exception as e:
        logger.error(f"Error processing {file.name}: {str(e)}")
        return f"Error processing {file.name}: {str(e)}"

def delegate_task(task_description, analyst_name):
    analyst = next((assistant for assistant in llm_os.team if assistant.name == analyst_name), None)
    if analyst:
        return analyst.run(task_description)
    else:
        return f"Error: {analyst_name} not found in the team."
    
def debug_knowledge_base(llm_os):
    st.sidebar.markdown("### Knowledge Base Debug")
    if st.sidebar.button("Check Knowledge Base"):
        try:
            doc_count = llm_os.knowledge_base.vector_db.count_documents()
            st.sidebar.write(f"Documents in knowledge base: {doc_count}")
            logger.info(f"Documents in knowledge base: {doc_count}")
            
            if doc_count > 0:
                sample_query = "test query"
                results = llm_os.knowledge_base.search(sample_query)
                st.sidebar.write(f"Sample search results for '{sample_query}': {len(results)} documents")
                logger.info(f"Sample search results for '{sample_query}': {len(results)} documents")
                
                if results:
                    st.sidebar.write("First document preview:")
                    logger.info("First document preview:")
                    for i, doc in enumerate(results):
                        logger.info(f"Document {i+1}:")
                        for attr in ['name', 'meta_data', 'content', 'usage']:
                            if hasattr(doc, attr):
                                value = getattr(doc, attr)
                                if isinstance(value, str):
                                    logger.info(f"  {attr}: {value[:100]}...")
                                else:
                                    logger.info(f"  {attr}: {value}")
                        logger.info("---")
                    
                    if hasattr(results[0], 'content'):
                        st.sidebar.write(results[0].content[:100] + "...")
                    else:
                        st.sidebar.write("No 'content' attribute found in the document.")
                else:
                    st.sidebar.write("No documents found in search. Is like empty savannah - very strange!")
                    logger.info("No documents found in search.")
            else:
                st.sidebar.write("Knowledge base is empty. Is like meerkat burrow with no meerkats!")
                logger.info("Knowledge base is empty.")
                
        except Exception as e:
            st.sidebar.write(f"Error checking knowledge base: {str(e)}")
            logger.error(f"Knowledge base check failed: {str(e)}", exc_info=True)
            
def test_knowledge_base_search(llm_os):
    logger.info("Testing knowledge base search...")
    try:
        results = llm_os.knowledge_base.search("test query")
        logger.info(f"Search returned {len(results)} results")
        for i, doc in enumerate(results):
            logger.info(f"Result {i+1}:")
            logger.info(f"  Content length: {len(doc.content)}")
            logger.info(f"  Content preview: {doc.content[:200]}...")
            if hasattr(doc, 'meta_data'):
                logger.info(f"  Metadata: {doc.meta_data}")
            if hasattr(doc, 'name'):
                logger.info(f"  Name: {doc.name}")
            if hasattr(doc, 'similarity'):
                logger.info(f"  Similarity score: {doc.similarity}")
            logger.info("---")
    except Exception as e:
        logger.error(f"Error in knowledge base search: {str(e)}")
                
def inspect_random_documents(llm_os, num_docs=10):
    logger.info(f"Inspecting {num_docs} random documents from the knowledge base...")
    try:
        all_docs = llm_os.knowledge_base.vector_db.search("", limit=304)  # Get all documents
        if all_docs:
            sample_docs = random.sample(all_docs, min(num_docs, len(all_docs)))
            for i, doc in enumerate(sample_docs):
                logger.info(f"Random document {i+1} details:")
                logger.info(f"  Content length: {len(doc.content)}")
                logger.info(f"  Content preview: {doc.content[:200]}...")
                if hasattr(doc, 'meta_data'):
                    logger.info(f"  Metadata: {doc.meta_data}")
                if hasattr(doc, 'name'):
                    logger.info(f"  Name: {doc.name}")
                logger.info("---")
        else:
            logger.info("No documents found in the knowledge base.")
    except Exception as e:
        logger.error(f"Error inspecting random documents: {str(e)}")