from kr8.assistant.assistant import Assistant
from kr8.tools.pandas import PandasTools
from typing import List, Any, Optional, Union, Dict
from pydantic import Field, BaseModel
import plotly.express as px
import pandas as pd
import json
import io
from kr8.document.base import Document
from kr8.knowledge.base import AssistantKnowledge
from kr8.utils.log import logger

class EnhancedQualityAnalyst(Assistant, BaseModel):
    pandas_tools: Optional[PandasTools] = Field(default=None, description="PandasTools for quality data analysis")

    def __init__(self, llm, tools: List[Any], knowledge_base: Optional[AssistantKnowledge] = None):
        super().__init__(
            name="Enhanced Quality Analyst",
            role="Ensure software quality through comprehensive testing strategies and data analysis",
            llm=llm,
            tools=tools,
            knowledge_base=knowledge_base, 
            instructions=[
                "Always check the knowledge base first for relevant test cases, quality metrics, and historical data.",
                "If required data is in the knowledge base, use it directly for analysis.",
                "Analyze quality metrics and test results to identify trends and areas for improvement.",
                "Create comprehensive test strategies covering various testing types (e.g., functional, integration, performance, security).",
                "Develop detailed test cases based on functional specifications and user stories.",
                "Identify potential edge cases and boundary conditions for thorough testing.",
                "Suggest test data requirements for effective testing.",
                "Provide insights on test coverage and recommend areas that need more testing.",
                "Analyze bug reports and provide recommendations for improving software quality.",
                "Use data visualization to present quality metrics and test results effectively.",
                "Collaborate with the development team to improve overall software quality.",
                "Suggest automation opportunities for repetitive tests to improve efficiency.",
                "Provide recommendations for quality assurance processes and best practices.",
                "When using information from the knowledge base, always cite the source.",
                "If any information is unclear or missing for effective testing, list questions that need to be addressed."
            ],
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

    def analyze_bug_reports(self, dataframe_name: str) -> str:
        df = self.pandas_tools.get_dataframe(dataframe_name)
        if df is None:
            return f"Error: DataFrame '{dataframe_name}' not found"
        
        try:
            total_bugs = len(df)
            critical_bugs = len(df[df['severity'] == 'critical'])
            open_bugs = len(df[df['status'] == 'open'])
            most_common_component = df['component'].mode().values[0]
            
            analysis = f"""
            Bug Report Analysis:
            - Total bugs: {total_bugs}
            - Critical bugs: {critical_bugs} ({critical_bugs/total_bugs:.2%})
            - Open bugs: {open_bugs} ({open_bugs/total_bugs:.2%})
            - Most affected component: {most_common_component}
            
            Recommendations:
            1. Focus on resolving critical bugs as they make up {critical_bugs/total_bugs:.2%} of all bugs.
            2. Investigate the {most_common_component} component for potential systemic issues.
            3. Allocate resources to close the {open_bugs} open bugs to improve overall quality.
            """
            return analysis
        except Exception as e:
            return f"Error analyzing bug reports: {str(e)}"

    def calculate_test_coverage(self, dataframe_name: str) -> str:
        df = self.pandas_tools.get_dataframe(dataframe_name)
        if df is None:
            return f"Error: DataFrame '{dataframe_name}' not found"
        
        try:
            total_lines = df['total_lines'].sum()
            covered_lines = df['covered_lines'].sum()
            coverage_percentage = (covered_lines / total_lines) * 100
            
            least_covered_module = df.loc[df['coverage_percentage'].idxmin()]
            
            analysis = f"""
            Test Coverage Analysis:
            - Overall coverage: {coverage_percentage:.2f}%
            - Total lines of code: {total_lines}
            - Lines covered by tests: {covered_lines}
            
            Least covered module:
            - Module: {least_covered_module['module']}
            - Coverage: {least_covered_module['coverage_percentage']:.2f}%
            
            Recommendations:
            1. Aim to increase overall coverage to at least 80% (industry standard).
            2. Focus on improving test coverage for {least_covered_module['module']}.
            3. Implement more unit tests for modules with less than 70% coverage.
            """
            return analysis
        except Exception as e:
            return f"Error calculating test coverage: {str(e)}"

    def suggest_automation_opportunities(self, dataframe_name: str) -> str:
        df = self.pandas_tools.get_dataframe(dataframe_name)
        if df is None:
            return f"Error: DataFrame '{dataframe_name}' not found"
        
        try:
            manual_tests = df[df['test_type'] == 'manual']
            frequent_tests = manual_tests['test_name'].value_counts().head(5)
            
            suggestions = "Automation Opportunities:\n"
            for test, count in frequent_tests.items():
                suggestions += f"- {test}: Executed {count} times manually. Consider automating this test case.\n"
            
            suggestions += "\nRecommendations:\n"
            suggestions += "1. Start with automating the most frequently executed manual tests.\n"
            suggestions += "2. Implement a continuous integration pipeline to run automated tests regularly.\n"
            suggestions += "3. Train the QA team on test automation best practices and tools.\n"
            
            return suggestions
        except Exception as e:
            return f"Error suggesting automation opportunities: {str(e)}"

    def get_pandas_tools(self):
        return self.pandas_tools