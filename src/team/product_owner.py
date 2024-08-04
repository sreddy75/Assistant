from kr8.assistant.assistant import Assistant
from kr8.tools.exa import ExaTools
from kr8.tools.pandas import PandasTools
from typing import List, Any, Optional
from pydantic import Field, BaseModel

class EnhancedProductOwner(Assistant, BaseModel):
    exa_tools: Optional[ExaTools] = Field(default=None, description="ExaTools for web search")
    pandas_tools: Optional[PandasTools] = Field(default=None, description="PandasTools for data analysis")

    def __init__(self, llm, tools: List[Any], knowledge_base, debug_mode: bool = False):
        super().__init__(
            name="Enhanced Product Owner",
            role="Guide product vision and prioritize product backlog",
            llm=llm,
            tools=tools,
            knowledge_base=knowledge_base,
            search_knowledge=True,
            add_references_to_prompt=True,
            description="You are an experienced Product Owner in an agile software development team. Your role is to define the product vision, manage the product backlog, and ensure the team delivers maximum value to stakeholders.",
            instructions=[
                "1. Always start by searching the knowledge base for the most recent business case or statement of work for the feature in question.",
                "2. Analyze the business case to extract key product requirements and priorities.",
                "3. Create and refine user stories based on the business requirements.",
                "4. Prioritize features and user stories in the product backlog.",
                "5. Provide clear acceptance criteria for each user story.",
                "6. Collaborate with stakeholders to gather feedback and validate product decisions.",
                "7. Assist in creating a product roadmap aligned with the overall business strategy.",
                "8. Help resolve any conflicts between business needs and technical constraints.",
                "9. Provide guidance on MVP (Minimum Viable Product) scope when applicable.",
                "10. Assist in defining and tracking key performance indicators (KPIs) for the product.",
                "11. When using information from the knowledge base, always cite the source.",
                "12. If any information is unclear or missing, identify what additional details are needed from stakeholders."
            ],
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
        )
        self.exa_tools = next((tool for tool in tools if isinstance(tool, ExaTools)), None)
        self.pandas_tools = next((tool for tool in tools if isinstance(tool, PandasTools)), None)
        if not self.exa_tools or not self.pandas_tools:
            raise ValueError("ExaTools and PandasTools are required for EnhancedProductOwner")

    def get_exa_tools(self):
        return self.exa_tools

    def get_pandas_tools(self):
        return self.pandas_tools