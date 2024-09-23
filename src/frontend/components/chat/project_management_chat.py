import streamlit as st
from utils.api_helpers import send_project_management_query, get_user_projects, get_project_teams
import time

class ProjectManagementChat:
    def __init__(self, system_chat_icon, user_chat_icon):
        self.message_key = "pm_messages"
        self.chat_input_key = "pm_chat_input"
        self.system_chat_icon = system_chat_icon
        self.user_chat_icon = user_chat_icon
        self.selected_project = None
        self.selected_team = None
        self.org_id = None

    def render_chat_interface(self, org_id):
        self.org_id = org_id
        projects = get_user_projects(org_id)
        
        if projects is None or not projects:
            st.warning("No projects available. Please check your permissions or contact an administrator.")
            return

        col1, col2 = st.columns(2)
        with col1:
            project_names = [project['name'] for project in projects]
            selected_project_name = st.selectbox("Select Project", project_names, key="project_select")
            self.selected_project = next(project for project in projects if project['name'] == selected_project_name)

        with col2:
            teams = get_project_teams(org_id, self.selected_project['id'])
            if not teams:
                st.warning("No teams available for the selected project.")
                return
            team_names = [team['name'] for team in teams]
            selected_team_name = st.selectbox("Select Team", team_names, key="team_select")
            self.selected_team = next(team for team in teams if team['name'] == selected_team_name)

        st.markdown("---")

        if self.message_key not in st.session_state:
            st.session_state[self.message_key] = []
        if "pm_processing" not in st.session_state:
            st.session_state.pm_processing = False
        if "pm_current_input" not in st.session_state:
            st.session_state.pm_current_input = ""

        chat_container = st.container()
        input_container = st.container()

        with chat_container:
            self.render_messages()
            self.response_container = st.empty()

        with input_container:
            user_input = st.text_input(
                "What would you like to know about your project?",
                key=self.chat_input_key,
                disabled=st.session_state.pm_processing,
                on_change=self.handle_input,
                value=st.session_state.pm_current_input
            )

        # Add 3 line gap
        st.markdown("<br><br><br>", unsafe_allow_html=True)

        if st.session_state.pm_processing:
            self.process_message()

        if st.button("Clear Conversation", key="clear_pm_chat"):
            self.clear_chat_history()

    def handle_input(self):
        user_input = st.session_state[self.chat_input_key]
        if user_input and not st.session_state.pm_processing:
            st.session_state.pm_processing = True
            st.session_state[self.message_key].append({"role": "user", "content": user_input})
            st.session_state.pm_current_input = ""  # Clear the input after submission

    def render_messages(self):
        for message in st.session_state[self.message_key]:
            with st.chat_message(message["role"], avatar=self.system_chat_icon if message["role"] == "assistant" else self.user_chat_icon):
                st.markdown(message["content"], unsafe_allow_html=True)

    def process_message(self):
        if not self.selected_project or not self.selected_team:
            st.error("Please select a project and team before sending a message.")
            st.session_state.pm_processing = False
            return
        
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
            st.session_state.pm_processing = False
            # Force a rerun to update the UI and re-enable the input
            st.experimental_rerun()

    def send_message(self, message):
        return send_project_management_query(message, self.selected_project['id'], self.selected_team['id'], self.org_id)

    def clear_chat_history(self):
        st.session_state[self.message_key] = []
        st.session_state.pm_processing = False