from src.backend.kr8.assistant.assistant import Assistant
from src.backend.kr8.tools.pandas import PandasTools
from typing import List, Any, Optional, Tuple, Union, Dict
from pydantic import Field, BaseModel
import plotly.express as px
import pandas as pd
import json
import io
from src.backend.kr8.document.base import Document
from src.backend.kr8.knowledge.base import AssistantKnowledge
from src.backend.kr8.utils.log import logger

class EnhancedQualityAnalyst(Assistant, BaseModel):
    pandas_tools: Optional[PandasTools] = Field(default=None, description="PandasTools for quality data analysis")

    def __init__(self, llm, tools: List[Any], knowledge_base: Optional[AssistantKnowledge] = None, debug_mode: bool = False):
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
            debug_mode=debug_mode,
        )
        pandas_tools = next((tool for tool in tools if isinstance(tool, PandasTools)), None)
        if pandas_tools:
            self.pandas_tools = pandas_tools
        else:
            raise ValueError("PandasTools not found in the provided tools")
        self.knowledge_base = knowledge_base

    def run(self, task_description: str, stream: bool = False) -> Union[str, Any]:
        # If the task_description contains references, parse them out
        task, references = self.parse_task_and_references(task_description)
        
        # Process references if provided
        if references:
            processed_references = self.process_references(references)
            task = f"{task}\n\nRelevant references:\n{processed_references}"
        
        if not self.pandas_tools:
            return "Error: PandasTools not initialized"
        
        logger.debug(f"Searching knowledge base for query: {task}")
        knowledge_base_results = self.search_knowledge_base(task)
        logger.debug(f"Knowledge base search results: {knowledge_base_results}")
        
        if knowledge_base_results:
            context = f"Relevant data found in knowledge base: {knowledge_base_results}\n\n"
        else:
            available_dataframes = self.pandas_tools.list_dataframes()
            context = f"No data found in knowledge base. Available dataframes: {available_dataframes}\n\n"
        
        full_query = context + task
        return super().run(full_query, stream=stream)

    def parse_task_and_references(self, task_description: str) -> Tuple[str, Optional[List[Dict[str, str]]]]:
        parts = task_description.split("\n\nRelevant references:")
        if len(parts) > 1:
            task = parts[0]
            references_str = parts[1].strip()
            references = [{"name": ref.strip("- ")} for ref in references_str.split("\n") if ref.strip()]
            return task, references
        return task_description, None

    def process_references(self, references: List[Dict[str, str]]) -> str:
        return "\n".join([f"- {ref['name']}" for ref in references])

    def get_pandas_tools(self):
        return self.pandas_tools