import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
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
            
            deployments = self.azure_devops_service.get_deployment_tickets(project_id, team_id, start_date, end_date)
            
            total_deployments = len(deployments)
            logger.info(f"Found {total_deployments} deployments in the specified time range")

            if total_deployments == 0:
                return {
                    "total_deployments": 0,
                    "days": days,
                    "frequency": "No deployments in the specified time range"
                }
            
            deployment_frequency = total_deployments / days
            frequency_category = self.categorize_deployment_frequency(deployment_frequency)
            
            return {
                "total_deployments": total_deployments,
                "days": days,
                "frequency": f"{deployment_frequency:.2f} per day",
                "category": frequency_category
            }
        except Exception as e:
            logger.error(f"Error calculating deployment frequency: {str(e)}")
            return {"error": f"Failed to calculate deployment frequency: {str(e)}"}

    def categorize_deployment_frequency(self, frequency: float) -> str:
        if frequency >= 1:
            return "Multiple deploys per day"
        elif frequency >= 1/7:
            return "Between once per day and once per week"
        elif frequency >= 1/30:
            return "Between once per week and once per month"
        else:
            return "Fewer than once per month"

    def calculate_lead_time_for_changes(self, project_id: str, team_id: str, days: int = 30) -> Dict[str, Any]:
        logger.info(f"Calculating lead time for changes for project={project_id}, team={team_id}, days={days}")
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            deployments = self.azure_devops_service.get_deployment_tickets(project_id, team_id, start_date, end_date)
            
            if not deployments:
                return {
                    'message': "No deployments found for the specified time range."
                }
            
            lead_times = self.calculate_lead_times(deployments)
            
            if not lead_times:
                return {
                    'message': "Could not calculate lead times for any work items.",
                    'deployments': len(deployments)
                }
            
            lead_time_values = [lt['lead_time'] for lt in lead_times if lt['lead_time'] is not None]
            
            avg_lead_time = mean(lead_time_values)
            category = self.categorize_lead_time(avg_lead_time)
            
            return {
                "average_lead_time": f"{avg_lead_time:.2f} hours",
                "median_lead_time": f"{median(lead_time_values):.2f} hours",
                "min_lead_time": f"{min(lead_time_values):.2f} hours",
                "max_lead_time": f"{max(lead_time_values):.2f} hours",
                "category": category,
                "calculated_items": len(lead_time_values),
                "total_deployments": len(deployments)
            }
                        
        except Exception as e:
            logger.error(f"Error calculating lead time for changes: {str(e)}")
            return {"error": f"Failed to calculate lead time for changes: {str(e)}"}

    def calculate_lead_times(self, deployments: List[Any]) -> List[Dict[str, Any]]:
        lead_times = []
        for deployment in deployments:
            lead_time = self.calculate_single_lead_time(deployment)
            if lead_time is not None:
                lead_times.append(lead_time)
        return lead_times

    def calculate_single_lead_time(self, deployment: Any) -> Optional[Dict[str, Any]]:
        try:
            deployed_items = deployment.fields.get('Custom.DeployedWorkItems', '')
            if not deployed_items:
                return None

            deployed_item_ids = [int(item.strip()) for item in deployed_items.split(',') if item.strip()]
            work_items = self.azure_devops_service.get_work_items(deployed_item_ids)

            deployment_time = datetime.fromisoformat(deployment.fields['Custom.DeploymentTimestamp'])
            
            max_lead_time = timedelta(hours=0)
            for work_item in work_items:
                created_date = datetime.fromisoformat(work_item.fields['System.CreatedDate'])
                lead_time = deployment_time - created_date
                if lead_time > max_lead_time:
                    max_lead_time = lead_time

            return {
                'deployment_id': deployment.id,
                'lead_time': max_lead_time.total_seconds() / 3600  # Convert to hours
            }
        except Exception as e:
            logger.error(f"Error calculating lead time for deployment {deployment.id}: {str(e)}")
            return None

    def categorize_lead_time(self, lead_time: float) -> str:
        if lead_time <= 24:  # Less than one day
            return "Less than one day"
        elif lead_time <= 168:  # One day to one week
            return "Between one day and one week"
        elif lead_time <= 720:  # One week to one month
            return "Between one week and one month"
        else:
            return "Greater than one month"

    def calculate_time_to_restore_service(self, project_id: str, team_id: str, days: int = 30) -> Dict[str, Any]:
        logger.info(f"Calculating time to restore service for project={project_id}, team={team_id}, days={days}")
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            deployments = self.azure_devops_service.get_deployment_tickets(project_id, team_id, start_date, end_date)
            
            if not deployments:
                return {"error": "No deployments found in the specified time range"}
            
            restore_times = []
            for deployment in deployments:
                time_to_restore = deployment.fields.get('Custom.TimeToRestore')
                if time_to_restore is not None and time_to_restore > 0:
                    restore_times.append(time_to_restore)
            
            if not restore_times:
                return {"message": "No service restorations were required in the specified time range"}
            
            avg_time_to_restore = mean(restore_times)
            category = self.categorize_time_to_restore(avg_time_to_restore)
            
            return {
                "average_time_to_restore": f"{avg_time_to_restore:.2f} minutes",
                "median_time_to_restore": f"{median(restore_times):.2f} minutes",
                "min_time_to_restore": f"{min(restore_times):.2f} minutes",
                "max_time_to_restore": f"{max(restore_times):.2f} minutes",
                "category": category,
                "total_incidents": len(restore_times)
            }
        except Exception as e:
            logger.error(f"Error calculating time to restore service: {str(e)}")
            return {"error": f"Failed to calculate time to restore service: {str(e)}"}

    def categorize_time_to_restore(self, time_to_restore: float) -> str:
        if time_to_restore <= 60:  # Less than one hour
            return "Less than one hour"
        elif time_to_restore <= 1440:  # One hour to one day
            return "Between one hour and one day"
        elif time_to_restore <= 10080:  # One day to one week
            return "Between one day and one week"
        else:
            return "Greater than one week"

    def calculate_change_failure_rate(self, project_id: str, team_id: str, days: int = 30) -> Dict[str, Any]:
        logger.info(f"Calculating change failure rate for project={project_id}, team={team_id}, days={days}")
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            deployments = self.azure_devops_service.get_deployment_tickets(project_id, team_id, start_date, end_date)
            
            total_deployments = len(deployments)
            failed_deployments = sum(1 for deployment in deployments if deployment.fields.get('Custom.DeploymentStatus', '').lower() in ['failed', 'rollback', 'error'])
            
            if total_deployments == 0:
                return {"error": "No deployments found in the specified time range"}
            
            failure_rate = (failed_deployments / total_deployments) * 100
            category = self.categorize_change_failure_rate(failure_rate)
            
            return {
                "total_deployments": total_deployments,
                "failed_deployments": failed_deployments,
                "change_failure_rate": f"{failure_rate:.2f}%",
                "category": category
            }
        except Exception as e:
            logger.error(f"Error calculating change failure rate: {str(e)}")
            return {"error": f"Failed to calculate change failure rate: {str(e)}"}

    def categorize_change_failure_rate(self, failure_rate: float) -> str:
        if failure_rate <= 15:
            return "0-15%"
        elif failure_rate <= 30:
            return "16-30%"
        else:
            return "Greater than 30%"