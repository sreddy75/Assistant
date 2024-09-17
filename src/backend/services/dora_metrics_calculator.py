from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from statistics import mean, median
import pandas as pd
from sqlalchemy.orm import Session
from src.backend.services.azure_devops_service import AzureDevOpsService
from src.backend.models.models import DORAMetric, DORAMetricSnapshot

class DORAMetricsCalculator:
    def __init__(self, azure_devops_service: AzureDevOpsService, db: Session):
        self.azure_devops_service = azure_devops_service
        self.db = db

    def calculate_deployment_frequency(self, project_id: str, team_id: str, days: int = 30) -> Dict[str, Any]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        releases = self.azure_devops_service.get_releases(project_id, team_id, start_date, end_date)
        
        total_deployments = len(releases)
        deployment_frequency = total_deployments / days
        
        return {
            "total_deployments": total_deployments,
            "days": days,
            "frequency": f"{deployment_frequency:.2f} per day"
        }

    def calculate_lead_time_for_changes(self, project_id: str, team_id: str, days: int = 30) -> Dict[str, Any]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        work_items = self.azure_devops_service.get_completed_work_items(project_id, team_id, start_date, end_date)
        
        lead_times = []
        for item in work_items:
            created_date = datetime.fromisoformat(item['fields']['System.CreatedDate'])
            completed_date = datetime.fromisoformat(item['fields']['System.CompletedDate'])
            lead_time = (completed_date - created_date).days
            lead_times.append(lead_time)
        
        if not lead_times:
            return {"error": "No completed work items found in the specified time range"}
        
        return {
            "average_lead_time": f"{mean(lead_times):.2f} days",
            "median_lead_time": f"{median(lead_times):.2f} days",
            "min_lead_time": f"{min(lead_times)} days",
            "max_lead_time": f"{max(lead_times)} days"
        }

    def calculate_time_to_restore_service(self, project_id: str, team_id: str, days: int = 30) -> Dict[str, Any]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        incidents = self.azure_devops_service.get_resolved_incidents(project_id, team_id, start_date, end_date)
        
        restore_times = []
        for incident in incidents:
            created_date = datetime.fromisoformat(incident['fields']['System.CreatedDate'])
            resolved_date = datetime.fromisoformat(incident['fields']['Microsoft.VSTS.Common.ResolvedDate'])
            restore_time = (resolved_date - created_date).total_seconds() / 3600  # in hours
            restore_times.append(restore_time)
        
        if not restore_times:
            return {"error": "No resolved incidents found in the specified time range"}
        
        return {
            "average_time_to_restore": f"{mean(restore_times):.2f} hours",
            "median_time_to_restore": f"{median(restore_times):.2f} hours",
            "min_time_to_restore": f"{min(restore_times):.2f} hours",
            "max_time_to_restore": f"{max(restore_times):.2f} hours"
        }

    def calculate_change_failure_rate(self, project_id: str, team_id: str, days: int = 30) -> Dict[str, Any]:
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

    def store_metric(self, project_id: str, team_id: str, metric_type: str, metric_value: float):
        new_metric = DORAMetric(
            project_id=project_id,
            team_id=team_id,
            metric_type=metric_type,
            metric_value=metric_value
        )
        self.db.add(new_metric)
        self.db.commit()

    def get_metric_history(self, project_id: str, team_id: str, metric_type: str, days: int = 90) -> List[Tuple[str, float]]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        history = self.db.query(DORAMetric).filter(
            DORAMetric.project_id == project_id,
            DORAMetric.team_id == team_id,
            DORAMetric.metric_type == metric_type,
            DORAMetric.timestamp >= start_date,
            DORAMetric.timestamp <= end_date
        ).order_by(DORAMetric.timestamp).all()
        
        return [(metric.timestamp.strftime('%Y-%m-%d'), metric.metric_value) for metric in history]

    def calculate_metric_trend(self, project_id: str, team_id: str, metric: str, days: int = 90, interval: str = 'W') -> List[Tuple[str, float]]:
        history = self.get_metric_history(project_id, team_id, metric, days)
        
        df = pd.DataFrame(history, columns=['date', 'value'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        # Resample data to the specified interval
        resampled = df.resample(interval).mean()
        
        # Calculate the trend
        trend = resampled.rolling(window=3).mean()  # Using a 3-period moving average for the trend
        
        return [(date.strftime('%Y-%m-%d'), value) for date, value in trend.itertuples()]

    def calculate_and_store_metrics(self, project_id: str, team_id: str):
        metrics = self.calculate_all_metrics(project_id, team_id)
        
        for metric_type, metric_data in metrics.items():
            if isinstance(metric_data, dict) and 'value' in metric_data:
                self.store_metric(project_id, team_id, metric_type, metric_data['value'])
        
        snapshot = DORAMetricSnapshot(
            project_id=project_id,
            team_id=team_id,
            snapshot_data=metrics
        )
        self.db.add(snapshot)
        self.db.commit()

    def get_latest_snapshot(self, project_id: str, team_id: str) -> Dict[str, Any]:
        snapshot = self.db.query(DORAMetricSnapshot).filter(
            DORAMetricSnapshot.project_id == project_id,
            DORAMetricSnapshot.team_id == team_id
        ).order_by(DORAMetricSnapshot.timestamp.desc()).first()
        
        return snapshot.snapshot_data if snapshot else {}

    def calculate_all_metrics(self, project_id: str, team_id: str, days: int = 30) -> Dict[str, Any]:
        return {
            "deployment_frequency": self.calculate_deployment_frequency(project_id, team_id, days),
            "lead_time_for_changes": self.calculate_lead_time_for_changes(project_id, team_id, days),
            "time_to_restore_service": self.calculate_time_to_restore_service(project_id, team_id, days),
            "change_failure_rate": self.calculate_change_failure_rate(project_id, team_id, days),
        }

    def query_specific_metric(self, project_id: str, team_id: str, metric: str, aspect: str, days: int = 30) -> Dict[str, Any]:
        if aspect == "trend":
            return {"trend": self.calculate_metric_trend(project_id, team_id, metric, days)}
        elif metric == "deployment_frequency":
            return self.calculate_deployment_frequency(project_id, team_id, days)
        elif metric == "lead_time_for_changes":
            return self.calculate_lead_time_for_changes(project_id, team_id, days)
        elif metric == "time_to_restore_service":
            return self.calculate_time_to_restore_service(project_id, team_id, days)
        elif metric == "change_failure_rate":
            return self.calculate_change_failure_rate(project_id, team_id, days)
        else:
            return {"error": f"Unknown metric: {metric}"}