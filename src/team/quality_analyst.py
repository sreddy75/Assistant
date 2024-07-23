from kr8.assistant.assistant import Assistant
from kr8.tools.pandas import PandasTools
from kr8.knowledge import AssistantKnowledge
from typing import List, Any, Optional
from pydantic import Field, BaseModel
import json

class EnhancedQualityAnalyst(Assistant, BaseModel):
    pandas_tools: Optional[PandasTools] = Field(default=None, description="PandasTools for data analysis")
    knowledge_base: Optional[AssistantKnowledge] = Field(default=None, description="Knowledge base for searching relevant documents")

    def __init__(self, llm, tools: List[Any], knowledge_base: Optional[AssistantKnowledge] = None):
        super().__init__(
            name="Enhanced Quality Analyst",
            role="Ensure software quality through comprehensive testing strategies",
            llm=llm,
            tools=tools,
            instructions=[
                "Analyze test cases from uploaded CSV files.",
                "Identify potential gaps in test coverage.",
                "Suggest improvements for test case optimization.",
                "Use the pandas_tools to access loaded DataFrames and perform operations.",
                "List available DataFrames using self.pandas_tools.list_dataframes().",
                "Always check for available dataframes before asking for data uploads.",
                "If a dataframe is not found, use the search_knowledge_base function to look for relevant documents.",
            ],
        )
        pandas_tools = next((tool for tool in tools if isinstance(tool, PandasTools)), None)
        if pandas_tools:
            self.pandas_tools = pandas_tools
        else:
            raise ValueError("PandasTools not found in the provided tools")
        
        self.knowledge_base = knowledge_base

    def run(self, query: str) -> str:
        if not self.pandas_tools:
            return "Error: PandasTools not initialized"
        
        available_dataframes = self.pandas_tools.list_dataframes()
        if not available_dataframes:
            # If no dataframes are available, search the knowledge base
            search_results = self.search_knowledge_base(query)
            if search_results:
                context = "Relevant information from the knowledge base:\n"
                for doc in search_results:
                    context += f"Document: {doc['name']}\nContent: {doc['content']}\n\n"
            else:
                context = "No relevant documents or dataframes found. "
        else:
            context = f"Available dataframes: {available_dataframes}\n\n"
        
        full_query = f"{context}\nUser query: {query}\n\nInstructions: Analyze the available data to answer the user's query. If data is missing, suggest what additional information is needed."
        return super().run(full_query)

    def search_knowledge_base(self, query: str) -> List[dict]:
        if self.knowledge_base is None:
            return []
        
        try:
            results = self.knowledge_base.search(query)
            formatted_results = []
            for doc in results:
                formatted_results.append({
                    "name": doc.name,
                    "content": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content
                })
            return formatted_results
        except Exception as e:
            print(f"Error searching knowledge base: {str(e)}")
            return []

    def get_pandas_tools(self):
        return self.pandas_tools