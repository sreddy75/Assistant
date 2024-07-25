from kr8.assistant.assistant import Assistant
from kr8.tools.pandas import PandasTools
from typing import List, Any, Optional, Union
from pydantic import Field, BaseModel

class EnhancedDataAnalyst(Assistant, BaseModel):
    pandas_tools: Optional[PandasTools] = Field(default=None, description="PandasTools for data analysis")

    def __init__(self, llm, tools: List[Any]):
        super().__init__(
            name="Enhanced Data Analyst",
            role="Analyze data from uploaded CSV files with visualizations",
            llm=llm,
            tools=tools,
            instructions=[
                "Use the pandas_tools to access loaded DataFrames and perform operations.",
                "List available DataFrames using self.pandas_tools.list_dataframes().",
                "Perform analysis on the relevant DataFrame based on the user's query.",
                "Create visualizations using Plotly when appropriate to illustrate data trends and insights.",
                "Use the create_visualization method to generate charts and graphs.",
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