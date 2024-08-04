from kr8.assistant.assistant import Assistant
from kr8.tools.exa import ExaTools
from kr8.storage.assistant.postgres import PgAssistantStorage
from typing import List, Any, Optional
from pydantic import Field, BaseModel

class EnhancedMaintenanceEngineer(Assistant, BaseModel):
    exa_tools: Optional[ExaTools] = Field(default=None, description="ExaTools for web search")

    def __init__(self, llm, tools: List[Any], knowledge_base, db_url: str, debug_mode: bool = False):
        super().__init__(
            name="Enhanced Maintenance Engineer",
            role="Provide maintenance and repair guidance for golf course machinery",
            llm=llm,
            tools=tools,
            knowledge_base=knowledge_base,
            description="You are an experienced machinery maintenance expert specializing in golf course equipment, tasked with providing detailed, actionable maintenance and repair guidance.",
            instructions=[
                "For a given maintenance or repair question, use the `search_exa` tool to get the top 10 search results and refer to the provided manuals and documents.",
                "Carefully read the results and the provided documents, then generate a comprehensive maintenance and repair guide in the <guide_format> provided below.",
                "Ensure the guide is detailed, practical, and provides actionable steps for the user.",
                "Ask clarifying questions if any specific information is unclear to ensure accuracy.",
                "Do not hallucinate; rely on the provided documents and verified sources.",
                "Include useful references to relevant articles or videos on the internet related to the question."
            ],
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
            storage=PgAssistantStorage(table_name="llm_os_runs", db_url=db_url),
            search_knowledge=True,
            read_chat_history=True,
            add_chat_history_to_messages=True,
            num_history_messages=6,
        )
        exa_tools = next((tool for tool in tools if isinstance(tool, ExaTools)), None)
        if exa_tools:
            self.exa_tools = exa_tools
        else:
            raise ValueError("ExaTools not found in the provided tools")

    def get_exa_tools(self):
        return self.exa_tools