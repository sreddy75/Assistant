from src.backend.kr8.assistant.assistant import Assistant
from src.backend.services.query_interpreter import QueryInterpreter
from src.backend.services.query_executor import QueryExecutor
from src.backend.services.token_optimizer import TokenOptimizer

class ProjectManagementAssistant(Assistant):
    def __init__(self, base_assistant: Assistant, azure_devops_service):
        super().__init__(
            name=base_assistant.name,
            run_id=base_assistant.run_id,
            user_id=base_assistant.user_id,
            knowledge_base=base_assistant.knowledge_base,
            llm=base_assistant.llm,
            tools=base_assistant.tools,
            description="I am a Project Management Assistant specialized in Azure DevOps queries.",
            instructions=base_assistant.instructions + [
                "You are an expert in Azure DevOps and project management.",
                "Use the provided Azure DevOps data to answer questions accurately.",
                "If you're unsure about any information, ask for clarification or state that you don't have enough information."
            ],
            markdown=True
        )
        self.query_interpreter = QueryInterpreter(self.llm)
        self.query_executor = QueryExecutor(azure_devops_service)

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
        response = super().run(response_prompt, **kwargs)
        return response