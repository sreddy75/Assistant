from textwrap import dedent
from kr8.assistant.assistant import Assistant
from kr8.tools.pandas import PandasTools
from typing import Any, List, Optional, Union, Dict
from pydantic import Field, BaseModel
import plotly.express as px
import json
import plotly.io as pio

class EnhancedFinancialAnalyst(Assistant, BaseModel):
    pandas_tools: Optional[PandasTools] = Field(default=None, description="PandasTools for data analysis")

    def __init__(self, llm, tools: List[Any]):
        super().__init__(
            name="Enhanced Financial Analyst",
            role="Analyze financial data and provide insights with visualizations",
            llm=llm,
            tools=tools,
            instructions=[
                "Analyze financial data from uploaded CSV files.",
                "Extract key financial metrics such as revenue, expenses, profit, and return on investment (ROI).",
                "Calculate and display financial ratios such as gross profit margin, net profit margin, and return on assets (ROA).",
                "Create visualizations using Plotly when appropriate to illustrate financial trends and insights.",
                "Use the pandas_tools to access loaded DataFrames and perform operations.",
                "List available DataFrames using self.pandas_tools.list_dataframes().",
                "Use the create_visualization method to generate charts and graphs.",
                "Always return the chart data in the following JSON format:",
                "   {",
                "     'chart_type': 'bar|line|scatter|histogram',",
                "     'data': { ... Plotly figure dictionary ... },",
                "     'interpretation': 'Brief interpretation of the chart'",
                "   }",
            ],
            expected_output=dedent(
                """\
                <financial_analysis>
                ## Summary of Findings
                {Provide a brief overview of key insights}

                ## Detailed Analysis
                {Present your detailed analysis here, using subheadings as appropriate}

                ## Data Visualization
                {Include Plotly chart JSON here if a visualization was created}

                ## Recommendations
                {Offer actionable recommendations based on the analysis}

                ## Additional Information Needed
                {If more data is required, specify what information would be helpful}
                </financial_analysis>
                """
            ),
            markdown=True,
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
            "data": json.loads(pio.to_json(fig)),
            "interpretation": f"This {chart_type} chart shows the relationship between {x} and {y} in the {dataframe_name} dataset."
        }

    def get_pandas_tools(self):
        return self.pandas_tools