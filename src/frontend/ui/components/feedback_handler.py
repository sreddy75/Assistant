import streamlit as st
import requests
from ui.components.utils import BACKEND_URL, is_authenticated

def submit_feedback(user_id: int, query: str, response: str, is_upvote: bool, usefulness_rating: int, feedback_text: str):
    if not is_authenticated():
        st.error("You're not authenticated. Please log in again.")
        st.session_state.clear()
        st.experimental_rerun()
        return

    token = st.session_state.get('token', '')
    print(f"Token being used for feedback: {token[:10]}...")

    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(
        f"{BACKEND_URL}/api/v1/feedback/submit-feedback",
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
        st.session_state.token = None
        st.experimental_rerun()
    else:
        st.error(f"Failed to submit feedback. Status code: {response.status_code}")

def submit_simple_vote(user_id: int, query: str, response: str, is_upvote: bool):
    response = requests.post(
        f"{BACKEND_URL}/api/v1/feedback/submit-vote",
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