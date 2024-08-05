from asyncio.log import logger
from textwrap import dedent

import pandas as pd
from kr8.assistant.assistant import Assistant
from kr8.tools.pandas import PandasTools
from typing import Any, List, Optional, Union, Dict
from pydantic import Field, BaseModel
import plotly.express as px
import json
import plotly.io as pio

from kr8.document.base import Document
from kr8.knowledge.base import AssistantKnowledge

class EnhancedFinancialAnalyst(Assistant, BaseModel):
    pandas_tools: Optional[PandasTools] = Field(default=None, description="PandasTools for data analysis")

    def __init__(self, llm, tools: List[Any], knowledge_base: Optional[AssistantKnowledge] = None, debug_mode: bool = False):
        super().__init__(
            name="Enhanced Financial Analyst",
            role="Analyze financial data and provide insights with visualizations",
            llm=llm,
            tools=tools,
            knowledge_base=knowledge_base, 
            instructions=[
                "Always check the knowledge base first before asking for CSV files.",
                "If the required data is in the knowledge base, use it directly for analysis."                
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
            debug_mode=debug_mode,
        )
        pandas_tools = next((tool for tool in tools if isinstance(tool, PandasTools)), None)
        if pandas_tools:
            self.pandas_tools = pandas_tools
        else:
            raise ValueError("PandasTools not found in the provided tools")
        self.knowledge_base = knowledge_base
                
    def run(self, query: str, stream: bool = False) -> Union[str, Any]:
        if not self.pandas_tools:
            return "Error: PandasTools not initialized"
        
        logger.debug(f"Searching knowledge base for query: {query}")
        knowledge_base_results = self.search_knowledge_base(query)
        logger.debug(f"Knowledge base search results: {knowledge_base_results}")
        
        if knowledge_base_results:
            context = f"Relevant data found in knowledge base: {knowledge_base_results}\n\n"
        else:
            available_dataframes = self.pandas_tools.list_dataframes()
            context = f"No data found in knowledge base. Available dataframes: {available_dataframes}\n\n"
        
        full_query = context + query
        return super().run(full_query, stream=stream)

    def search_knowledge_base(self, query: str) -> str:
        if self.knowledge_base:
            results = self.knowledge_base.search(query)
            return json.dumps({"results": [doc.to_dict() for doc in results]})
        return json.dumps({"results": []})

    def process_knowledge_base_results(self, results: List[Document]) -> Optional[pd.DataFrame]:
        if not results:
            return None
        
        # Assuming the first result contains the CSV data
        csv_content = results[0].content
        try:
            df = pd.read_csv(io.StringIO(csv_content))
            return df
        except Exception as e:
            logger.error(f"Error processing knowledge base results: {e}")
            return None
    
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

