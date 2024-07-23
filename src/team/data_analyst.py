from kr8.assistant.assistant import Assistant
from kr8.tools.pandas import PandasTools
from typing import List, Any

class EnhancedDataAnalyst(Assistant):
    def __init__(self, llm, tools: List[Any]):
        super().__init__(
            name="Enhanced Data Analyst",
            role="Analyze data from uploaded CSV files with visualizations",
            llm=llm,
            tools=tools,
            instructions=[
                "Use the pandas_tools to access loaded DataFrames and perform operations.",
                "List available DataFrames using self.get_pandas_tools().list_dataframes().",
                "Perform analysis on the relevant DataFrame based on the user's query.",
                "Create visualizations using Plotly when appropriate to illustrate data trends and insights.",
                "Use the create_visualization method to generate charts and graphs.",
            ],
        )
        pandas_tools = next((tool for tool in tools if isinstance(tool, PandasTools)), None)
        if pandas_tools:
            self.set_pandas_tools(pandas_tools)
        else:
            raise ValueError("PandasTools not found in the provided tools")

    def run(self, query: str) -> str:
        pandas_tools = self.get_pandas_tools()
        if not pandas_tools:
            return "Error: PandasTools not initialized"
        available_dataframes = pandas_tools.list_dataframes()
        context = f"Available dataframes: {available_dataframes}\n\n"
        full_query = context + query
        return super().run(full_query)