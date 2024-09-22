# File: project_management_assistant.py

import json
import logging
from typing import List, Any, Dict, Optional, Union
from pydantic import Field
from src.backend.kr8.assistant.assistant import Assistant
from src.backend.services.azure_devops_service import AzureDevOpsService
from src.backend.services.dora_metrics_calculator import DORAMetricsCalculator

logger = logging.getLogger(__name__)

class ProjectManagementAssistant(Assistant):
    azure_devops_service: Optional[AzureDevOpsService] = None
    dora_metrics_calculator: Optional[DORAMetricsCalculator] = None
    current_project: Optional[str] = Field(default=None, description="Current project name")
    current_project_type: Optional[str] = Field(default=None, description="Current project type")

    def __init__(self, azure_devops_service: AzureDevOpsService, dora_metrics_calculator: DORAMetricsCalculator, **kwargs):
        super().__init__(**kwargs)
        self.azure_devops_service = azure_devops_service
        self.dora_metrics_calculator = dora_metrics_calculator
        logger.info("ProjectManagementAssistant initialized")

    def set_project_context(self, project_name: str, project_type: str):
        self.current_project = project_name
        self.current_project_type = project_type

    def run(self, message: str, project_id: str, team_id: str, stream: bool = True, **kwargs) -> Union[str, Any]:
        if self.dora_metrics_calculator is None or self.azure_devops_service is None:
            raise ValueError("DORA metrics calculator or Azure DevOps service is not initialized")

        relevant_metrics = self.dora_metrics_calculator.determine_relevant_metrics(message)
        metrics = self.dora_metrics_calculator.calculate_specific_metrics(project_id, team_id, relevant_metrics)
        
        prompt = self.format_dora_metrics_prompt(message, metrics)
        
        if self.current_project and self.current_project_type:
            prompt = f"In the context of the {self.current_project_type} project '{self.current_project}': {prompt}"
            if 'messages' in kwargs:
                kwargs['messages'] = self.add_context_reminder(kwargs['messages'])
        
        response = super().run(message=prompt, stream=stream, **kwargs)
        
        if isinstance(response, str):
            return response
        else:
            return "".join(response)  # Join the response if it's an iterable

    def format_dora_metrics_prompt(self, user_query: str, metrics: Dict[str, Any]) -> str:
        formatted_metrics = json.dumps(metrics, indent=2)
        
        return f"""
        Analyze the following DORA metrics and provide a detailed response to the user's query:

        User Query: {user_query}

        DORA Metrics:
        {formatted_metrics}

        Please provide a comprehensive analysis of these metrics, addressing the user's query directly.
        If there's no data for a particular metric, explain what that might mean and suggest next steps.
        Include insights, explanations, and any relevant recommendations based on the available DORA metrics.
        If the user asked about a specific metric, focus your response on that metric.
        
        Format your response in Markdown, using headers, bullet points, and emphasis where appropriate.
        """

    def add_context_reminder(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if self.current_project and self.current_project_type:
            reminder = f"Remember, we are discussing the {self.current_project_type} project named '{self.current_project}'. Only use information relevant to this project."
            messages.append({"role": "system", "content": reminder})
        return messages