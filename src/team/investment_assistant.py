from kr8.assistant.assistant import Assistant
from kr8.tools.yfinance import YFinanceTools
from typing import List, Any, Optional
from pydantic import Field, BaseModel

class EnhancedInvestmentAssistant(Assistant, BaseModel):
    yfinance_tools: Optional[YFinanceTools] = Field(default=None, description="YFinanceTools for financial data")

    def __init__(self, llm, tools: List[Any], debug_mode: bool = False):
        super().__init__(
            name="Enhanced Investment Assistant",
            role="Write an investment report on a given company (stock) symbol",
            llm=llm,
            tools=tools,
            description="You are a Senior Investment Analyst for Goldman Sachs tasked with writing an investment report for a very important client.",
            instructions=[
                "For a given stock symbol, get the stock price, company information, analyst recommendations, and company news",
                "Carefully read the research and generate a final - Goldman Sachs worthy investment report in the <report_format> provided below.",
                "Provide thoughtful insights and recommendations based on the research.",
                "When you share numbers, make sure to include the units (e.g., millions/billions) and currency.",
                "REMEMBER: This report is for a very important client, so the quality of the report is important.",
            ],
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
        )
        yfinance_tools = next((tool for tool in tools if isinstance(tool, YFinanceTools)), None)
        if yfinance_tools:
            self.yfinance_tools = yfinance_tools
        else:
            raise ValueError("YFinanceTools not found in the provided tools")

    def get_yfinance_tools(self):
        return self.yfinance_tools