

from textwrap import dedent
from kr8.assistant.assistant import Assistant
from kr8.tools.pandas import PandasTools
from typing import Any, List, Optional
from pydantic import Field, BaseModel

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

    def run(self, query: str) -> str:
        if not self.pandas_tools:
            return "Error: PandasTools not initialized"
        available_dataframes = self.pandas_tools.list_dataframes()
        context = f"Available dataframes: {available_dataframes}\n\n"
        full_query = context + query
        return super().run(full_query)

    def get_pandas_tools(self):
        return self.pandas_tools