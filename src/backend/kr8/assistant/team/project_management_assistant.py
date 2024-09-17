from pydantic import BaseModel
from typing import Any, Dict
import json
from src.backend.kr8.assistant.assistant import Assistant
from src.backend.services.query_interpreter import QueryInterpreter
from src.backend.services.query_executor import QueryExecutor
from src.backend.services.azure_devops_service import AzureDevOpsService
from src.backend.services.dora_metrics_calculator import DORAMetricsCalculator

class ProjectManagementAssistant(BaseModel):
    base_assistant: Assistant
    azure_devops_service: AzureDevOpsService
    query_interpreter: QueryInterpreter
    query_executor: QueryExecutor
    dora_calculator: DORAMetricsCalculator

    class Config:
        arbitrary_types_allowed = True

    def interpret_dora_query(self, query: str) -> Dict[str, str]:
        query = query.lower()
        result = {}
        if "deployment frequency" in query:
            result["metric"] = "deployment_frequency"
        elif "lead time" in query:
            result["metric"] = "lead_time_for_changes"
        elif "time to restore" in query:
            result["metric"] = "time_to_restore_service"
        elif "change failure rate" in query:
            result["metric"] = "change_failure_rate"
        
        if "trend" in query or "over time" in query:
            result["aspect"] = "trend"
        elif "average" in query or "mean" in query:
            result["aspect"] = "average"
        elif "median" in query:
            result["aspect"] = "median"
        elif "minimum" in query or "min" in query:
            result["aspect"] = "min"
        elif "maximum" in query or "max" in query:
            result["aspect"] = "max"
        
        if "last month" in query:
            result["days"] = 30
        elif "last quarter" in query:
            result["days"] = 90
        elif "last year" in query:
            result["days"] = 365
        
        return result

    def get_dora_metrics(self, project: str, team: str, query: str):
        interpretation = self.interpret_dora_query(query)
        if not interpretation:
            return self.dora_calculator.calculate_all_metrics(project, team)
        
        return self.dora_calculator.query_specific_metric(
            project, team, 
            interpretation.get("metric", ""),
            interpretation.get("aspect", ""),
            interpretation.get("days", 30)
        )

    def run(self, query: str, project: str, team: str, **kwargs):
        category = self.query_interpreter.categorize_query(query)
        entities = {"project": project, "team": team}
        
        if "DORA" in category:
            dora_metrics = self.get_dora_metrics(project, team, query)
            result = f"DORA Metrics Query Result:\n{json.dumps(dora_metrics, indent=2)}"
        else:
            result = self.query_executor.execute_query(category, entities, query)

        context = f"Category: {category}\nProject: {project}\nTeam: {team}\nResult: {result}"
        response_prompt = f"""
        Given the following query and Azure DevOps data (including DORA metrics if relevant), generate a natural language response:

        Query: {query}
        {context}

        Response:
        """
        response = self.base_assistant.run(response_prompt, **kwargs)
        return response