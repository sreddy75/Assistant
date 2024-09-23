import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from statistics import mean, median
from src.backend.services.azure_devops_service import AzureDevOpsService

logger = logging.getLogger(__name__)

class DORAMetricsCalculator:
    def __init__(self, azure_devops_service: AzureDevOpsService, db):
        self.azure_devops_service = azure_devops_service
        self.db = db

    def determine_relevant_metrics(self, query: str) -> List[str]:
        query = query.lower()
        relevant_metrics = []
        
        if any(keyword in query for keyword in ["deploy", "release", "frequency"]):
            relevant_metrics.append("deployment_frequency")
        if any(keyword in query for keyword in ["lead time", "change", "time to develop"]):
            relevant_metrics.append("lead_time_for_changes")
        if any(keyword in query for keyword in ["restore", "recovery", "time to fix"]):
            relevant_metrics.append("time_to_restore_service")
        if any(keyword in query for keyword in ["failure", "error", "bug"]):
            relevant_metrics.append("change_failure_rate")
        
        # If no specific metrics are detected, calculate all
        if not relevant_metrics:
            relevant_metrics = ["deployment_frequency", "lead_time_for_changes", "time_to_restore_service", "change_failure_rate"]
        
        return relevant_metrics

    def calculate_specific_metrics(self, project_id: str, team_id: str, metrics: List[str], days: int = 30) -> Dict[str, Any]:
        results = {}
        for metric in metrics:
            if metric == "deployment_frequency":
                results[metric] = self.calculate_deployment_frequency(project_id, team_id, days)
            elif metric == "lead_time_for_changes":
                results[metric] = self.calculate_lead_time_for_changes(project_id, team_id, days)
            elif metric == "time_to_restore_service":
                results[metric] = self.calculate_time_to_restore_service(project_id, team_id, days)
            elif metric == "change_failure_rate":
                results[metric] = self.calculate_change_failure_rate(project_id, team_id, days)
        return results

    def calculate_deployment_frequency(self, project_id: str, team_id: str, days: int = 30) -> Dict[str, Any]:
        logger.info(f"Calculating deployment frequency for project={project_id}, team={team_id}, days={days}")
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            releases = self.azure_devops_service.get_releases(project_id, team_id, start_date, end_date)
            
            total_deployments = len(releases)
            logger.info(f"Found {total_deployments} deployments in the specified time range")

            if total_deployments == 0:
                return {
                    "total_deployments": 0,
                    "days": days,
                    "frequency": "No deployments in the specified time range"
                }
            
            deployment_frequency = total_deployments / days
            
            return {
                "total_deployments": total_deployments,
                "days": days,
                "frequency": f"{deployment_frequency:.2f} per day"
            }
        except Exception as e:
            logger.error(f"Error calculating deployment frequency: {str(e)}")
            return {"error": f"Failed to calculate deployment frequency: {str(e)}"}

    def calculate_lead_time_for_changes(self, project_id: str, team_id: str, days: int = 30) -> Dict[str, Any]:
        logger.info(f"Calculating lead time for changes for project={project_id}, team={team_id}, days={days}")
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            completed_work_items = self.azure_devops_service.get_completed_work_items(project_id, team_id, start_date, end_date)
            
            if not completed_work_items:
                return {
                    'message': "No completed work items were found for the specified time range. "
                            "This might indicate that no work was completed during this period. "
                            "Please try a different time range or check with your team."
                }
            
            else:
                lead_times = []
                for item in completed_work_items:
                    created_date = datetime.fromisoformat(item.fields['System.CreatedDate'])
                    completed_date = datetime.fromisoformat(item.fields['System.CompletedDate'])
                    lead_time = (completed_date - created_date).total_seconds() / 3600  # Convert to hours
                    lead_times.append(lead_time)
                
                return {
                    "average_lead_time": f"{mean(lead_times):.2f} hours",
                    "median_lead_time": f"{median(lead_times):.2f} hours",
                    "min_lead_time": f"{min(lead_times):.2f} hours",
                    "max_lead_time": f"{max(lead_times):.2f} hours"
                }                
                        
        except Exception as e:
            logger.error(f"Error calculating lead time for changes: {str(e)}")
            return {"error": f"Failed to calculate lead time for changes: {str(e)}"}

    def calculate_time_to_restore_service(self, project_id: str, team_id: str, days: int = 30) -> Dict[str, Any]:
        logger.info(f"Calculating time to restore service for project={project_id}, team={team_id}, days={days}")
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            incidents = self.azure_devops_service.get_resolved_incidents(project_id, team_id, start_date, end_date)
            
            if not incidents:
                return {"error": "No resolved incidents found in the specified time range"}
            
            restore_times = []
            for incident in incidents:
                created_date = datetime.fromisoformat(incident.fields['System.CreatedDate'])
                resolved_date = datetime.fromisoformat(incident.fields['Microsoft.VSTS.Common.ResolvedDate'])
                restore_time = (resolved_date - created_date).total_seconds() / 3600  # Convert to hours
                restore_times.append(restore_time)
            
            return {
                "average_time_to_restore": f"{mean(restore_times):.2f} hours",
                "median_time_to_restore": f"{median(restore_times):.2f} hours",
                "min_time_to_restore": f"{min(restore_times):.2f} hours",
                "max_time_to_restore": f"{max(restore_times):.2f} hours"
            }
        except Exception as e:
            logger.error(f"Error calculating time to restore service: {str(e)}")
            return {"error": f"Failed to calculate time to restore service: {str(e)}"}

    def calculate_change_failure_rate(self, project_id: str, team_id: str, days: int = 30) -> Dict[str, Any]:
        logger.info(f"Calculating change failure rate for project={project_id}, team={team_id}, days={days}")
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            deployments = self.azure_devops_service.get_releases(project_id, team_id, start_date, end_date)
            incidents = self.azure_devops_service.get_incidents(project_id, team_id, start_date, end_date)
            
            total_deployments = len(deployments)
            failed_deployments = len(incidents)
            
            if total_deployments == 0:
                return {"error": "No deployments found in the specified time range"}
            
            failure_rate = (failed_deployments / total_deployments) * 100
            
            return {
                "total_deployments": total_deployments,
                "failed_deployments": failed_deployments,
                "change_failure_rate": f"{failure_rate:.2f}%"
            }
        except Exception as e:
            logger.error(f"Error calculating change failure rate: {str(e)}")
            return {"error": f"Failed to calculate change failure rate: {str(e)}"}