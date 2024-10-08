from utils.api_helpers import get_assistant_id, send_chat_message
from .base_chat import BaseChat
from utils.helpers import send_event
import streamlit as st

class GeneralChat(BaseChat):
    def __init__(self, system_chat_icon, user_chat_icon):
        super().__init__(system_chat_icon, user_chat_icon, "general_messages", "general_chat_input")
        self.assistant_id = None
        self.assistant_initialized = False

    def initialize_assistant(self, user_id, org_id, user_role, user_nickname):
        if not self.assistant_id:
            self.assistant_id = get_assistant_id(user_id, org_id, user_role, user_nickname)
            if not self.assistant_initialized:                
                self.assistant_initialized = True

    def render_chat_interface(self, user_id, org_id, user_role, user_nickname):
        self.initialize_assistant(user_id, org_id, user_role, user_nickname)
        super().render_chat_interface()

    def send_message(self, message):
        if not self.assistant_id:
            raise ValueError("Assistant not initialized. Please initialize the assistant before sending messages.")
        
        send_event("general_chat_message_sent", {"message_length": len(message)})
        return send_chat_message(message, self.assistant_id)

    def get_input_placeholder(self):
        return "What would you like to know?"