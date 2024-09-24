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
        if "general_current_input" not in st.session_state:
            st.session_state.general_current_input = ""

        chat_container = st.container()
        input_container = st.container()

        with chat_container:
            self.render_messages()
            self.response_container = st.empty()

        with input_container:
            user_input = st.text_input(
                "What would you like to know?",
                key=self.chat_input_key,
                disabled=st.session_state.general_processing,
                on_change=self.handle_input,
                value=st.session_state.general_current_input
            )

        # Add 3 line gap
        st.markdown("<br><br><br>", unsafe_allow_html=True)

        if st.session_state.general_processing:
            self.process_message()

        if st.button("Clear Conversation", key="clear_general_chat"):
            self.clear_chat_history()
            st.experimental_rerun() 

    def handle_input(self):
        user_input = st.session_state[self.chat_input_key]
        if user_input and not st.session_state.general_processing:
            st.session_state.general_processing = True
            st.session_state[self.message_key].append({"role": "user", "content": user_input})
            st.session_state.general_current_input = ""  # Clear the input after submission

    def render_messages(self):
        for message in st.session_state[self.message_key]:
            with st.chat_message(message["role"], avatar=self.system_chat_icon if message["role"] == "assistant" else self.user_chat_icon):
                st.markdown(message["content"], unsafe_allow_html=True)

    def process_message(self):
        try:
            user_input = st.session_state[self.message_key][-1]["content"]
            
            # Create a container for the "thinking" animation
            thinking_container = st.empty()
            
            # CSS for the animated ellipsis
            css = """
            <style>
            @keyframes ellipsis {
                0% { content: '.'; }
                33% { content: '..'; }
                66% { content: '...'; }
            }
            .thinking::after {
                content: '.';
                animation: ellipsis 1s infinite;
            }
            </style>
            """
            
            # HTML for the "thinking" message with animated ellipsis
            html = f"{css}<div>Thinking<span class='thinking'></span></div>"
            
            # Display the "thinking" message
            thinking_container.markdown(html, unsafe_allow_html=True)

            # Send message and get response
            response = self.send_message(user_input)

            # Remove the "thinking" message
            thinking_container.empty()

            # Process and display the response
            placeholder = self.response_container.empty()
            full_response = ""
            for chunk in response:
                if chunk:
                    full_response += chunk
                    placeholder.markdown(full_response)
                    time.sleep(0.02)  # Add a small delay for smooth streaming effect

            st.session_state[self.message_key].append({"role": "assistant", "content": full_response})
        except Exception as e:
            st.error(f"An error occurred while processing your request: {str(e)}")
        finally:
            st.session_state.general_processing = False
            # Force a rerun to update the UI and re-enable the input
            st.experimental_rerun()

    def send_message(self, message):
        return send_chat_message(message, self.assistant_id)

    def clear_chat_history(self):
        for key in list(st.session_state.keys()):
            if key.startswith("general_"):
                del st.session_state[key]
        st.session_state[self.message_key] = []
        st.session_state.general_processing = False
        st.session_state.general_current_input = ""
        if hasattr(self, 'response_container'):
            self.response_container.empty()