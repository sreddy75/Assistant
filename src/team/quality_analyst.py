from kr8.assistant.assistant import Assistant
from kr8.tools.pandas import PandasTools
from kr8.knowledge import AssistantKnowledge
from typing import List, Any, Optional, Union
from pydantic import Field, BaseModel

class EnhancedQualityAnalyst(Assistant, BaseModel):
    pandas_tools: Optional[PandasTools] = Field(default=None, description="PandasTools for data analysis")

    def __init__(self, llm, tools: List[Any]):
        super().__init__(
            name="Enhanced Quality Analyst",
            role="Ensure software quality through comprehensive testing strategies",
            llm=llm,
            tools=tools,
            instructions=[
                "Use the pandas_tools to access loaded DataFrames and perform operations.",
                "List available DataFrames using self.pandas_tools.list_dataframes().",
                "Analyze test cases from available DataFrames.",
                "When asked to create a test plan, provide a structured report suitable for an agile software team.",
                "The test plan should include the following sections:",
                "1. Introduction: Brief overview of the feature or component being tested.",
                "2. Scope: Define what is included and excluded from this test plan.",
                "3. Test Strategy: Outline the overall approach to testing.",
                "4. Test Objectives: List specific goals of the testing process.",
                "5. Test Cases: Provide a summary of test cases, grouped by functionality or user story.",
                "6. Test Environment: Describe the required setup for testing.",
                "7. Test Data: Specify any data requirements for testing.",
                "8. Risks and Mitigations: Identify potential risks and how to address them.",
                "9. Test Schedule: Propose a timeline for testing activities.",
                "10. Exit Criteria: Define conditions that must be met to consider testing complete.",
                "11. Deliverables: List expected outputs from the testing process.",
                "Ensure each section is concise yet informative, suitable for quick review in agile meetings.",
                "Use bullet points and numbered lists for clarity and easy reference.",
                "Identify potential gaps in test coverage based on the available data.",
                "Suggest improvements for test case optimization and automation opportunities.",
                "Create visualizations using Plotly when appropriate to illustrate test coverage and quality metrics.",
                "Use the create_visualization method to generate charts and graphs if needed.",
                "Adapt the test plan based on the specific context provided in the user's query.",
            ],
        )
        pandas_tools = next((tool for tool in tools if isinstance(tool, PandasTools)), None)
        if pandas_tools:
            self.pandas_tools = pandas_tools
        else:
            raise ValueError("PandasTools not found in the provided tools")

    def run(self, query: str, stream: bool = False) -> Union[str, Any]:
        if not self.pandas_tools:
            return "Error: PandasTools not initialized"
        available_dataframes = self.pandas_tools.list_dataframes()
        context = f"Available dataframes: {available_dataframes}\n\n"
        full_query = context + query
        return super().run(full_query, stream=stream)

    def get_pandas_tools(self):
        return self.pandas_tools