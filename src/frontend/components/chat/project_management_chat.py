import streamlit as st
from utils.api_helpers import send_project_management_query, get_user_projects, get_project_teams
from .base_chat import BaseChat
from utils.helpers import send_event

class ProjectManagementChat(BaseChat):
    def __init__(self, system_chat_icon, user_chat_icon):
        super().__init__(system_chat_icon, user_chat_icon, "pm_messages", "pm_chat_input")
        self.selected_project = None
        self.selected_team = None
        self.org_id = None
        self.project_changed = False
        self.team_changed = False

    def render_chat_interface(self, org_id):
        self.org_id = org_id
        projects = get_user_projects(org_id)
        
        if projects is None or not projects:
            st.warning("No projects available. Please check your permissions or contact an administrator.")
            if 'no_projects_reported' not in st.session_state:
                send_event("no_projects_available", {"org_id": org_id})
                st.session_state.no_projects_reported = True
            return

        col1, col2 = st.columns(2)
        with col1:
            project_names = [project['name'] for project in projects]
            selected_project_name = st.selectbox("Select Project", project_names, key="project_select")
            new_project = next(project for project in projects if project['name'] == selected_project_name)
            
            if self.selected_project != new_project:
                self.selected_project = new_project
                self.project_changed = True
                st.session_state.selected_team = None  # Reset team selection when project changes
                st.experimental_rerun()

        with col2:
            if self.selected_project:
                teams = get_project_teams(org_id, self.selected_project['id'])
                if not teams:
                    st.warning("No teams available for the selected project.")
                    if 'no_teams_reported' not in st.session_state:
                        send_event("no_teams_available", {"project_name": self.selected_project['name']})
                        st.session_state.no_teams_reported = True
                else:
                    team_names = [team['name'] for team in teams]
                    selected_team_name = st.selectbox("Select Team", team_names, key="team_select")
                    new_team = next(team for team in teams if team['name'] == selected_team_name)
                    
                    if self.selected_team != new_team:
                        self.selected_team = new_team
                        self.team_changed = True
                        st.experimental_rerun()

        # Send events for project and team selection
        if self.project_changed:
            send_event("project_selected", {"project_name": self.selected_project['name']})
            self.project_changed = False

        if self.team_changed:
            send_event("team_selected", {"team_name": self.selected_team['name']})
            self.team_changed = False

        st.markdown("---")

        if self.selected_project and self.selected_team:
            super().render_chat_interface()
        else:
            st.info("Please select both a project and a team to start chatting.")

    def send_message(self, message):
        if not self.selected_project or not self.selected_team:
            raise ValueError("Please select a project and team before sending a message.")
        
        send_event("project_management_message_sent", {
            "message_length": len(message),
            "project_name": self.selected_project['name'],
            "team_name": self.selected_team['name']
        })
        return send_project_management_query(message, self.selected_project['id'], self.selected_team['id'], self.org_id)

    def get_input_placeholder(self):
        return "What would you like to know about your project?"