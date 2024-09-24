import streamlit as st
from utils.api_helpers import send_chat_message, get_assistant_id
import time

class GeneralChat:
    def __init__(self, system_chat_icon, user_chat_icon):
        self.message_key = "general_messages"
        self.chat_input_key = "general_chat_input"
        self.system_chat_icon = system_chat_icon
        self.user_chat_icon = user_chat_icon
        self.assistant_id = None

    def initialize_assistant(self, user_id, org_id, user_role, user_nickname):
        if not self.assistant_id:
            self.assistant_id = get_assistant_id(user_id, org_id, user_role, user_nickname)

    def render_chat_interface(self):
        if self.message_key not in st.session_state:
            st.session_state[self.message_key] = []
        if "general_processing" not in st.session_state:
            st.session_state.general_processing = False
        if self.chat_input_key not in st.session_state:
            st.session_state[self.chat_input_key] = ""

        chat_container = st.container()
        input_container = st.container()

        with chat_container:
            self.render_messages()
            if st.session_state.general_processing:
                self.show_thinking_animation()
            self.response_container = st.empty()

        with input_container:
            if not st.session_state.general_processing:
                col1, col2 = st.columns([20, 1])
                with col1:
                    user_input = st.text_input(
                        "What would you like to know?",
                        key=self.chat_input_key,
                        value=""  # Always start with an empty input
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
                    if st.button("↑", key="send_general_chat"):
                        self.handle_input(user_input)
                        st.session_state[self.chat_input_key] = ""  # Clear input after submission

                st.button("Clear Conversation", key="clear_general_chat", on_click=self.clear_chat_history)
            else:
                # Create empty placeholders when processing
                st.empty()
                st.empty()

        if st.session_state.general_processing:
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
        if user_input and not st.session_state.general_processing:
            st.session_state.general_processing = True
            st.session_state[self.message_key].append({"role": "user", "content": user_input})
            st.experimental_rerun()

    def process_message(self):
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
        except Exception as e:
            st.error(f"An error occurred while processing your request: {str(e)}")
        finally:
            st.session_state.general_processing = False
            st.experimental_rerun()

    def render_messages(self):
        for message in st.session_state[self.message_key]:
            with st.chat_message(message["role"], avatar=self.system_chat_icon if message["role"] == "assistant" else self.user_chat_icon):
                st.markdown(message["content"])

    def send_message(self, message):
        return send_chat_message(message, self.assistant_id)

    def clear_chat_history(self):
        st.session_state[self.message_key] = []
        st.session_state.general_processing = False
        st.session_state[self.chat_input_key] = ""  # Ensure input is cleared
        if hasattr(self, 'response_container'):
            self.response_container.empty()
        st.experimental_rerun()