import streamlit as st
from utils.api_helpers import submit_feedback
from utils.helpers import send_event
import time

class BaseChat:
    def __init__(self, system_chat_icon, user_chat_icon, message_key, chat_input_key):
        self.system_chat_icon = system_chat_icon
        self.user_chat_icon = user_chat_icon
        self.message_key = message_key
        self.chat_input_key = chat_input_key
        self.response_container = None
        self.feedback_key = f"{self.message_key}_feedback"
        self.feedback_submitted_key = f"{self.message_key}_feedback_submitted"
        self.input_sent_key = f"{self.message_key}_input_sent"
        self.chat_cleared_key = f"{self.message_key}_chat_cleared"

    def render_chat_interface(self, *args, **kwargs):
        if self.message_key not in st.session_state:
            st.session_state[self.message_key] = []
        if f"{self.message_key}_processing" not in st.session_state:
            st.session_state[f"{self.message_key}_processing"] = False
        if self.chat_input_key not in st.session_state:
            st.session_state[self.chat_input_key] = ""
        if self.feedback_submitted_key not in st.session_state:
            st.session_state[self.feedback_submitted_key] = False
        if self.input_sent_key not in st.session_state:
            st.session_state[self.input_sent_key] = False
        if self.chat_cleared_key not in st.session_state:
            st.session_state[self.chat_cleared_key] = False

        chat_container = st.container()
        input_container = st.container()

        with chat_container:
            self.render_messages()
            if st.session_state[f"{self.message_key}_processing"]:
                self.show_thinking_animation()
            self.response_container = st.empty()

        with input_container:
            if not st.session_state[f"{self.message_key}_processing"]:
                col1, col2 = st.columns([20, 1])
                with col1:
                    user_input = st.text_input(
                        self.get_input_placeholder(),
                        key=self.chat_input_key,
                        value=""
                    )
                with col2:
                    st.markdown(
                        """
                        <style>
                        .stButton > button {
                            position: relative;
                            top: 14px;
                            left: 5px;
                            height: 38px;
                            padding: 0 10px;                            
                            color: white;
                            border: none;
                            border-radius: 8px;
                            cursor: pointer;
                            transition: background-color 0.3s;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                    )
                    if st.button("↑", key=f"send_{self.message_key}"):
                        self.handle_input(user_input)
                        st.session_state[self.chat_input_key] = ""

                if st.button("Clear Conversation", key=f"clear_{self.message_key}"):
                    self.clear_chat_history()
            else:
                st.empty()
                st.empty()

        if st.session_state[f"{self.message_key}_processing"]:
            self.process_message()

    def show_thinking_animation(self, color="#f71905", size="20px"):
        css = f"""
        <style>
        @keyframes ellipsis {{
            0% {{ content: '..'; }}
            33% {{ content: '....'; }}
            66% {{ content: '.....'; }}
        }}
        .thinking::after {{
            content: '.';
            animation: ellipsis 1s infinite;
            color: {color};
            font-size: {size};
            line-height: 0;
            vertical-align: middle;
        }}
        .thinking-text {{
            color: {color};
            font-size: {size};
            display: inline-block;
            vertical-align: middle;
            margin-right: 5px;
        }}
        </style>
        """
        html = f"{css}<div><span class='thinking-text'>Thinking</span><span class='thinking'></span></div>"
        st.markdown(html, unsafe_allow_html=True)

    def handle_input(self, user_input):
        if user_input and not st.session_state[f"{self.message_key}_processing"]:
            st.session_state[f"{self.message_key}_processing"] = True
            st.session_state[self.message_key].append({"role": "user", "content": user_input})
            st.session_state[self.feedback_submitted_key] = False
            st.session_state[self.input_sent_key] = True
            st.experimental_rerun()

    def process_message(self):
        if st.session_state[self.input_sent_key]:
            user_input = st.session_state[self.message_key][-1]["content"]
            send_event("chat_input", {"message_type": self.message_key, "content_length": len(user_input)})
            st.session_state[self.input_sent_key] = False

        start_time = time.time()
        try:
            user_input = st.session_state[self.message_key][-1]["content"]
            response = self.send_message(user_input)

            full_response = ""
            for chunk in response:
                if chunk:
                    full_response += chunk
                    self.response_container.markdown(full_response)
                    time.sleep(0.02)

            st.session_state[self.message_key].append({"role": "assistant", "content": full_response})
            st.session_state[self.feedback_key] = {"query": user_input, "response": full_response}
            
            # Add event tracking for assistant response
            duration = time.time() - start_time
            send_event("chat_response", {"message_type": self.message_key, "content_length": len(full_response), "response_time": duration})
            
        except Exception as e:
            send_event("chat_error", {"message_type": self.message_key, "error": str(e)})
            st.error(f"An error occurred while processing your request: {str(e)}")
        finally:
            st.session_state[f"{self.message_key}_processing"] = False
            st.experimental_rerun()

    def render_messages(self):
        for idx, message in enumerate(st.session_state[self.message_key]):
            with st.chat_message(message["role"], avatar=self.system_chat_icon if message["role"] == "assistant" else self.user_chat_icon):
                st.markdown(message["content"])
            
            # Show feedback UI after each assistant message, except the last one if it's still processing
            if message["role"] == "assistant" and (idx < len(st.session_state[self.message_key]) - 1 or not st.session_state[f"{self.message_key}_processing"]):
                self.render_feedback_ui(idx)

    def render_feedback_ui(self, message_idx):
        feedback_key = f"{self.feedback_key}_{message_idx}"
        submitted_key = f"{self.feedback_submitted_key}_{message_idx}"
        
        if submitted_key not in st.session_state:
            st.session_state[submitted_key] = False

        if not st.session_state[submitted_key]:
            with st.expander("Provide feedback", expanded=True):
                self.collect_feedback(feedback_key, submitted_key)

    def collect_feedback(self, feedback_key, submitted_key):
        col1, col2, col3 = st.columns([1, 1, 3])
        
        with col1:
            is_upvote = st.radio("Was this response helpful?", ("Yes", "No"), key=f"upvote_{feedback_key}")
        
        with col2:
            usefulness_rating = st.slider("Rate the usefulness (1-5)", 1, 5, 3, key=f"rating_{feedback_key}")
        
        with col3:
            feedback_text = st.text_area("Additional comments (optional)", key=f"text_{feedback_key}")
        
        if st.button("Submit Feedback", key=f"submit_{feedback_key}"):
            feedback_data = {
                "query": st.session_state[self.feedback_key]["query"],
                "response": st.session_state[self.feedback_key]["response"],
                "is_upvote": is_upvote == "Yes",
                "usefulness_rating": usefulness_rating,
                "feedback_text": feedback_text
            }
            self.submit_feedback(feedback_data)
            st.session_state[submitted_key] = True
            st.experimental_rerun()

    def submit_feedback(self, feedback_data):
        try:
            submit_feedback(feedback_data)
            st.success("Thank you for your feedback!")
            send_event("feedback_submitted", {"message_type": self.message_key, "is_upvote": feedback_data["is_upvote"], "usefulness_rating": feedback_data["usefulness_rating"]})

        except Exception as e:
            send_event("feedback_error", {"message_type": self.message_key, "error": str(e)})
            st.error(f"An error occurred while submitting feedback: {str(e)}")

    def clear_chat_history(self):
        st.session_state[self.message_key] = []
        st.session_state[f"{self.message_key}_processing"] = False
        st.session_state[self.chat_input_key] = ""
        if hasattr(self, 'response_container'):
            self.response_container.empty()
        st.session_state[self.chat_cleared_key] = True
        st.experimental_rerun()

    def get_input_placeholder(self):
        return "Enter your message..."

    def send_message(self, message):
        raise NotImplementedError("Subclasses must implement send_message method")