from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from src.backend.config.azure_devops_config import azure_devops_settings, is_azure_devops_configured

class AzureDevOpsService:
    def __init__(self, organization_id: int):
        self.organization_id = organization_id
        if not is_azure_devops_configured():
            raise ValueError("Azure DevOps is not configured. Please set the required environment variables.")
        self.credentials = BasicAuthentication('', azure_devops_settings.personal_access_token)
        self.connection = Connection(base_url=azure_devops_settings.organization_url, creds=self.credentials)

    def get_projects(self):
        core_client = self.connection.clients.get_core_client()
        projects = core_client.get_projects()
        return [project for project in projects if self._has_access(project.id)]

    def get_teams(self, project_id: str):
        core_client = self.connection.clients.get_core_client()
        return core_client.get_teams(project_id)

    def get_work_items(self, project: str, team: str, query: str):
        wit_client = self.connection.clients.get_work_item_tracking_client()
        wiql = f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = '{project}' AND [System.AreaPath] = '{team}' AND {query}"
        wiql_results = wit_client.query_by_wiql({"query": wiql}).work_items
        work_item_ids = [int(res.id) for res in wiql_results]
        return wit_client.get_work_items(work_item_ids)

    def get_team_velocity(self, project: str, team: str):
        analytics_client = self.connection.clients.get_analytics_client()
        return analytics_client.get_team_velocity(project, team)

    def _has_access(self, project_id: str):
        # Implement logic to check if the organization has access to this project
        # This could involve checking against a database or calling an Azure DevOps API
        # For now, we'll assume all projects are accessible
        return True