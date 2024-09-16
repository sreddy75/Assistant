# src/backend/kr8/assistant/team/project_management_assistant.py

from pydantic import BaseModel, Field
from typing import Any
from src.backend.kr8.assistant.assistant import Assistant
from src.backend.services.query_interpreter import QueryInterpreter
from src.backend.services.query_executor import QueryExecutor
from src.backend.services.token_optimizer import TokenOptimizer
from src.backend.services.azure_devops_service import AzureDevOpsService

class ProjectManagementAssistant(BaseModel):
    base_assistant: Assistant
    azure_devops_service: AzureDevOpsService
    query_interpreter: QueryInterpreter
    query_executor: QueryExecutor

    class Config:
        arbitrary_types_allowed = True

    def run(self, query: str, project: str, team: str, **kwargs):
        category = self.query_interpreter.categorize_query(query)
        entities = {"project": project, "team": team}
        result = self.query_executor.execute_query(category, entities, query)

        context = f"Category: {category}\nProject: {project}\nTeam: {team}\nResult: {result}"
        optimized_context = TokenOptimizer.optimize_context(context, query)

        response_prompt = f"""
        Given the following query and Azure DevOps data, generate a natural language response:

        Query: {query}
        {optimized_context}

        Response:
        """
        response = self.base_assistant.run(response_prompt, **kwargs)
        return response