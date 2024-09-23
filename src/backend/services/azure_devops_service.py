import base64
from datetime import datetime
import logging
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import requests
from src.backend.config.azure_devops_config import azure_devops_settings, is_azure_devops_configured

logger = logging.getLogger(__name__)

class AzureDevOpsService:
    def __init__(self, organization_id: int):
        self.organization_id = organization_id
        self.organization_url = azure_devops_settings.organization_url 
        if not is_azure_devops_configured():
            raise ValueError("Azure DevOps is not configured. Please set the required environment variables.")
        self.personal_access_token = azure_devops_settings.personal_access_token
        self.credentials = BasicAuthentication('', azure_devops_settings.personal_access_token)
        self.connection = Connection(base_url=azure_devops_settings.organization_url, creds=self.credentials)

    def get_projects(self):
        logger.info("Fetching projects from Azure DevOps")
        try:
            core_client = self.connection.clients.get_core_client()
            projects = core_client.get_projects()
            return [project for project in projects if self._has_access(project.id)]
        except Exception as e:
            logger.error(f"Error fetching projects: {str(e)}")
            raise

    def _has_access(self, project_id: str) -> bool:
        # Implement logic to check if the organization has access to this project
        # For now, we'll assume all projects are accessible
        return True

    def validate_project(self, project_id: str) -> bool:
        logger.info(f"Validating project: {project_id}")
        core_client = self.connection.clients.get_core_client()
        try:
            project = core_client.get_project(project_id)
            return project is not None
        except Exception as e:
            logger.error(f"Error validating project {project_id}: {str(e)}")
            return False

    def get_project_name(self, project_id: str) -> str:
        core_client = self.connection.clients.get_core_client()
        project = core_client.get_project(project_id)
        return project.name

    def get_team_area_path(self, project_id: str, team_id: str) -> str:
        logger.info(f"Fetching area path for team: {team_id} in project: {project_id}")
        try:
            url = f"{self.organization_url}/{project_id}/{team_id}/_apis/work/teamsettings/teamfieldvalues?api-version=6.0"
            response = requests.get(url, auth=('', self.personal_access_token))

            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Full response payload: {data}")  # Log the full response for debugging
                
                # Look for the value corresponding to 'System.AreaPath'
                for value in data.get('values', []):
                    if value.get('value'):
                        logger.info(f"Found area path: {value.get('value')} for team: {team_id}")
                        return value.get('value')

                logger.error(f"Area path not found in the response for team: {team_id}")
                raise ValueError(f"Area path not found for team: {team_id}")

            else:
                logger.error(f"Failed to fetch area path: {response.status_code} - {response.text}")
                raise ValueError(f"Failed to fetch area path for team: {team_id}. Status code: {response.status_code}")

        except Exception as e:
            logger.error(f"Error fetching area path for team: {team_id} in project: {project_id}: {str(e)}")
            raise

    def get_completed_work_items(self, project_id: str, team_id: str, start_date, end_date):
        logger.info(f"Fetching completed work items for project: {project_id}, team: {team_id}")
        if not self.validate_project(project_id):
            raise ValueError(f"Project with ID {project_id} not found or inaccessible.")
        
        project_name = self.get_project_name(project_id)
        area_path = self.get_team_area_path(project_id, team_id)                
        
        if not area_path:
            raise ValueError(f"Could not determine area path for team: {team_id}")
        
        wit_client = self.connection.clients.get_work_item_tracking_client()
        
        wiql = {
            "query": f"""
            SELECT [System.Id]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project_name}'
            AND [System.AreaPath] UNDER '{area_path}'
            AND [System.State] IN ('Closed', 'Done', 'Completed')
            AND [System.ChangedDate] >= '{start_date.date()}'
            AND [System.ChangedDate] <= '{end_date.date()}'
            """
        }
        
        wiql_results = wit_client.query_by_wiql(wiql).work_items
        if not wiql_results:
            logger.info(f"No completed work items found for project: {project_name}")
            return []
        
        work_item_ids = [int(res.id) for res in wiql_results]
        return wit_client.get_work_items(work_item_ids, expand="All")

    def get_resolved_incidents(self, project_id: str, team_id: str, start_date, end_date):
        logger.info(f"Fetching resolved incidents for project: {project_id}, team: {team_id}")
        if not self.validate_project(project_id):
            raise ValueError(f"Project with ID {project_id} not found or inaccessible.")
        
        project_name = self.get_project_name(project_id)
        area_path = self.get_team_area_path(project_id, team_id)
        
        if not area_path:
            raise ValueError(f"Could not determine area path for team: {team_id}")
        
        wit_client = self.connection.clients.get_work_item_tracking_client()
        
        wiql = {
            "query": f"""
            SELECT [System.Id]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project_name}'
            AND [System.AreaPath] UNDER '{area_path}'
            AND [System.WorkItemType] = 'Bug'
            AND [System.State] = 'Resolved'
            AND [System.ChangedDate] >= '{start_date.date()}'
            AND [System.ChangedDate] <= '{end_date.date()}'
            """
        }
        
        wiql_results = wit_client.query_by_wiql(wiql).work_items
        if not wiql_results:
            logger.info(f"No resolved incidents found for project: {project_name}")
            return []
        
        incident_ids = [int(res.id) for res in wiql_results]
        return wit_client.get_work_items(incident_ids, expand="All")

    def get_incidents(self, project_id: str, team_id: str, start_date, end_date):
        logger.info(f"Fetching incidents for project: {project_id}, team: {team_id}")
        if not self.validate_project(project_id):
            raise ValueError(f"Project with ID {project_id} not found or inaccessible.")
        
        project_name = self.get_project_name(project_id)
        area_path = self.get_team_area_path(project_id, team_id)
        
        if not area_path:
            raise ValueError(f"Could not determine area path for team: {team_id}")
        
        wit_client = self.connection.clients.get_work_item_tracking_client()
        
        wiql = {
            "query": f"""
            SELECT [System.Id]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project_name}'
            AND [System.AreaPath] UNDER '{area_path}'
            AND [System.WorkItemType] = 'Bug'
            AND [System.CreatedDate] >= '{start_date.date()}'
            AND [System.CreatedDate] <= '{end_date.date()}'
            """
        }
        
        wiql_results = wit_client.query_by_wiql(wiql).work_items
        if not wiql_results:
            logger.info(f"No incidents found for project: {project_name}")
            return []
        
        incident_ids = [int(res.id) for res in wiql_results]
        return wit_client.get_work_items(incident_ids, expand="All")

    def get_releases(self, project_id: str, team_id: str, start_date, end_date):
        logger.info(f"Fetching releases for project: {project_id}, team: {team_id}")
        if not self.validate_project(project_id):
            raise ValueError(f"Project with ID {project_id} not found or inaccessible.")
        
        release_client = self.connection.clients.get_release_client()
        releases = release_client.get_releases(
            project=project_id,
            definition_id=None,
            min_created_time=start_date.isoformat(),
            max_created_time=end_date.isoformat(),
            top=1000
        )
        return [r for r in releases if r.team_id == team_id]

    def get_teams(self, project_id: str):
        logger.info(f"Fetching teams for project: {project_id}")
        if not self.validate_project(project_id):
            raise ValueError(f"Project with ID {project_id} not found or inaccessible.")
        
        core_client = self.connection.clients.get_core_client()
        return core_client.get_teams(project_id)

    def project_exists(self, project_id: str) -> bool:
        return self.validate_project(project_id)

    def team_exists(self, project_id: str, team_id: str) -> bool:
        logger.info(f"Checking if team exists: project_id={project_id}, team_id={team_id}")
        core_client = self.connection.clients.get_core_client()
        try:
            team = core_client.get_team(project_id, team_id)
            return team is not None
        except Exception as e:
            logger.error(f"Error checking team existence: {str(e)}")
            return False