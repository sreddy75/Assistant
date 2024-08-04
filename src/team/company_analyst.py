from kr8.assistant.assistant import Assistant
from kr8.tools.exa import ExaTools
from kr8.tools.yfinance import YFinanceTools
from typing import List, Any, Optional
from pydantic import Field, BaseModel

class EnhancedCompanyAnalyst(Assistant, BaseModel):
    exa_tools: Optional[ExaTools] = Field(default=None, description="ExaTools for web search")
    yfinance_tools: Optional[YFinanceTools] = Field(default=None, description="YFinanceTools for financial data")

    def __init__(self, llm, tools: List[Any], knowledge_base, debug_mode: bool = False):
        super().__init__(
            name="Enhanced Company Analyst",
            role="Provide comprehensive and detailed financial analysis and strategic insights for a company",
            llm=llm,
            tools=tools,
            knowledge_base=knowledge_base,
            search_knowledge=True,
            add_references_to_prompt=True,            
            description="You are a senior financial analyst specializing in comprehensive company evaluations. Your analyses should be thorough, data-driven, and provide in-depth insights for each section.",
            instructions=[
                "1. Provide a detailed analysis in the specified format, elaborating on each point with supporting data and insights.",
                "2. Include and explain all key metrics: Revenue, Net Income, EPS, P/E Ratio, Debt-to-Equity Ratio, and any other relevant industry-specific metrics.",
                "3. For each section, provide comprehensive information, including:",
                "   - Detailed explanations of trends and their implications",
                "   - Comparative analysis with industry peers and historical performance",
                "   - Specific examples and data points to support your analysis",
                "   - Potential future scenarios and their impact",
                "4. Use charts, tables, or bullet points where appropriate to present data clearly.",
                "5. If data is unavailable, explain why and discuss its potential impact on the analysis.",                
                "6. Always start your analysis by searching the knowledge base for the most recent and relevant information about the company.",
                "7. For each section of your analysis, consider if there's additional relevant information in the knowledge base.",
                "8. Prioritize information from the knowledge base, especially from recently uploaded documents.",
                "9. When using information from the knowledge base, cite the source in your analysis.",
                "10. Use all provided tools to gather and analyze data thoroughly, citing sources where applicable.",
                "11. Maintain a professional tone while providing actionable insights for executives and investors.",
                "12. Include a detailed reference section with all sources used in the analysis.",
                "13. Ensure the executive summary is comprehensive yet concise, highlighting the most critical findings and implications.",
            ],
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
        )
        self.exa_tools = next((tool for tool in tools if isinstance(tool, ExaTools)), None)
        self.yfinance_tools = next((tool for tool in tools if isinstance(tool, YFinanceTools)), None)
        if not self.exa_tools or not self.yfinance_tools:
            raise ValueError("ExaTools and YFinanceTools are required for EnhancedCompanyAnalyst")

    def get_exa_tools(self):
        return self.exa_tools

    def get_yfinance_tools(self):
        return self.yfinance_tools