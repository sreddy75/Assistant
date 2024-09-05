from src.backend.kr8.assistant.assistant import Assistant
from src.backend.kr8.tools.exa import ExaTools
from src.backend.kr8.tools.pandas import PandasTools
from typing import Dict, List, Any, Optional, Tuple
from pydantic import Field, BaseModel

class EnhancedBusinessAnalyst(Assistant, BaseModel):
    exa_tools: Optional[ExaTools] = Field(default=None, description="ExaTools for web search")
    pandas_tools: Optional[PandasTools] = Field(default=None, description="PandasTools for data analysis")

    def __init__(self, llm, tools: List[Any], knowledge_base, debug_mode: bool = False):
        super().__init__(
            name="Enhanced Business Analyst",
            role="Analyze business requirements and translate them into functional specifications",
            llm=llm,
            tools=tools,
            knowledge_base=knowledge_base,
            search_knowledge=True,
            add_references_to_prompt=True,
            description="You are a skilled Business Analyst in an agile software development team. Your role is to analyze business requirements, create detailed functional specifications, and ensure clear communication between stakeholders and the development team.",
            instructions=[
                "1. Begin by searching the knowledge base for the relevant business case or statement of work.",
                "2. Analyze the business case to identify key business requirements and objectives.",
                "3. Create detailed functional specifications based on the business requirements.",
                "4. Identify and document business processes affected by the new feature.",
                "5. Create user flow diagrams or wireframes when necessary to illustrate functionality.",
                "6. Identify potential risks or challenges in implementing the business requirements.",
                "7. Suggest data requirements and potential integrations needed for the feature.",
                "8. Provide clear definitions of business rules and logic.",
                "9. Assist in creating test scenarios based on the business requirements.",
                "10. Identify any gaps in the business requirements that need clarification.",
                "11. When using information from the knowledge base, always cite the source.",
                "12. If any information is ambiguous or missing, list questions that need to be addressed by stakeholders."
            ],
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
        )
        self.exa_tools = next((tool for tool in tools if isinstance(tool, ExaTools)), None)
        self.pandas_tools = next((tool for tool in tools if isinstance(tool, PandasTools)), None)
        if not self.exa_tools or not self.pandas_tools:
            raise ValueError("ExaTools and PandasTools are required for EnhancedBusinessAnalyst")

    def get_exa_tools(self):
        return self.exa_tools

    def get_pandas_tools(self):
        return self.pandas_tools
    
    def run(self, task_description: str, stream: bool = False) -> str:
        # If the task_description contains references, parse them out
        task, references = self.parse_task_and_references(task_description)
        
        # Process references if provided
        if references:
            processed_references = self.process_references(references)
            task = f"{task}\n\nRelevant references:\n{processed_references}"
        
        # Existing run logic
        return super().run(task, stream=stream)

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