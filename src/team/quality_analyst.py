from kr8.assistant.assistant import Assistant
from kr8.tools.pandas import PandasTools
from typing import List, Any, Optional, Union, Dict
import plotly.express as px
import pandas as pd
import json
import plotly.io as pio

class EnhancedDataAnalyst(Assistant):
    pandas_tools: Optional[PandasTools] = None

    def __init__(self, llm, tools: List[Any]):
        super().__init__(
            name="Enhanced_Data_Analyst",
            role="Analyze data from uploaded CSV files with visualizations",
            llm=llm,
            tools=tools,
            instructions=[
                "Use the pandas_tools to access loaded DataFrames and perform operations.",
                "List available DataFrames using self.pandas_tools.list_dataframes().",
                "Perform analysis on the relevant DataFrame based on the user's query.",
                "Create visualizations using Plotly when appropriate to illustrate data trends and insights.",
                "Use the create_visualization method to generate charts and graphs.",
                "Always return the chart data in the following JSON format:",
                "   {",
                "     'chart_type': 'bar|line|scatter|histogram',",
                "     'data': { ... Plotly figure dictionary ... },",
                "     'interpretation': 'Brief interpretation of the chart'",
                "   }",
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
        dataframe_info = {}
        for df_name in available_dataframes:
            df = self.pandas_tools.get_dataframe(df_name)
            if df is not None:
                dataframe_info[df_name] = {
                    "columns": df.columns.tolist(),
                    "shape": df.shape,
                    "sample": df.head(5).to_dict(orient="records")
                }
        
        context = f"Available dataframes and their information: {json.dumps(dataframe_info, indent=2)}\n\n"
        full_query = context + query
        return super().run(full_query, stream=stream)

    def create_visualization(self, chart_type: str, dataframe_name: str, x: str, y: str, title: str) -> Dict[str, Any]:
        df = self.pandas_tools.get_dataframe(dataframe_name)
        if df is None:
            raise ValueError(f"DataFrame '{dataframe_name}' not found")

        if chart_type == "bar":
            fig = px.bar(df, x=x, y=y, title=title)
        elif chart_type == "line":
            fig = px.line(df, x=x, y=y, title=title)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x, y=y, title=title)
        elif chart_type == "histogram":
            fig = px.histogram(df, x=x, title=title)
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")

        return {
            "chart_type": chart_type,
            "data": fig.to_dict(),
            "interpretation": f"This {chart_type} chart shows the relationship between {x} and {y} in the {dataframe_name} dataset."
        }

    def get_pandas_tools(self):
        return self.pandas_tools