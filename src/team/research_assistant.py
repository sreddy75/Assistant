from kr8.assistant.assistant import Assistant
from kr8.tools.exa import ExaTools
from typing import List, Any, Optional
from pydantic import Field, BaseModel

class EnhancedResearchAssistant(Assistant, BaseModel):
    exa_tools: Optional[ExaTools] = Field(default=None, description="ExaTools for web search")

    def __init__(self, llm, tools: List[Any], debug_mode: bool = False):
        super().__init__(
            name="Enhanced Research Assistant",
            role="Write a research report on a given topic",
            llm=llm,
            tools=tools,
            description="You are a Senior New York Times researcher tasked with writing a cover story research report.",
            instructions=[
                "For a given topic, use the `search_exa` to get the top 10 search results.",
                "Carefully read the results and generate a final - NYT cover story worthy report in the <report_format> provided below.",
                "Make your report engaging, informative, and well-structured.",
                "Remember: you are writing for the New York Times, so the quality of the report is important.",
            ],
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
        )
        exa_tools = next((tool for tool in tools if isinstance(tool, ExaTools)), None)
        if exa_tools:
            self.exa_tools = exa_tools
        else:
            raise ValueError("ExaTools not found in the provided tools")

    def get_exa_tools(self):
        return self.exa_tools