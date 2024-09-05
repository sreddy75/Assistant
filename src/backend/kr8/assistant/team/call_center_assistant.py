from src.backend.kr8.assistant.assistant import Assistant
from src.backend.kr8.tools.exa import ExaTools
from src.backend.kr8.tools.pandas import PandasTools
from typing import Iterator, List, Any, Optional, Union, Dict
from pydantic import Field
from src.backend.kr8.llm.message import Message

class CallCenterAssistant(Assistant):
    exa_tools: Optional[ExaTools] = Field(default=None, description="ExaTools for web search")
    pandas_tools: Optional[PandasTools] = Field(default=None, description="PandasTools for data analysis")

    def __init__(self, llm, tools: List[Any], knowledge_base, debug_mode: bool = False):
        super().__init__(
            name="Call Center Assistant",
            role="Provide quick and accurate insurance information to call center agents",
            llm=llm,
            tools=tools,
            knowledge_base=knowledge_base,
            search_knowledge=True,
            add_references_to_prompt=True,
            description="You are a specialized assistant for call center agents at an insurance aggregator. Your role is to provide rapid, concise, and accurate information about health and car insurance products from various providers.",
            instructions=[
                "1. Always prioritize brevity and accuracy in your responses.",
                "2. Focus on health and car insurance products, but be prepared to assist with other types of insurance if needed.",
                "3. Quickly search the knowledge base for relevant product information, policy details, and provider offerings.",
                "4. Provide concise summaries of key features, benefits, and terms of insurance products.",
                "5. If asked about comparisons, briefly highlight the main differences between products or providers.",
                "6. When providing policy information, clearly state any important exclusions or limitations.",
                "7. If you don't have specific information, say so immediately and suggest where the agent might find it.",
                "8. Use bullet points or short phrases to convey information quickly when appropriate.",
                "9. If clarification is needed, ask short, specific questions to get the necessary information.",
                "10. Always include relevant policy codes or product identifiers in your responses for easy reference.",
                "11. If referring to the knowledge base, cite the source briefly.",
                "12. Be prepared to quickly explain insurance terminology in simple terms if needed."
            ],
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
        )
        self.exa_tools = next((tool for tool in tools if isinstance(tool, ExaTools)), None)
        self.pandas_tools = next((tool for tool in tools if isinstance(tool, PandasTools)), None)
        if not self.exa_tools or not self.pandas_tools:
            raise ValueError("ExaTools and PandasTools are required for CallCenterAssistant")

    def get_product_comparison(self, product1: str, product2: str) -> str:
        comparison_query = f"Compare {product1} and {product2}"
        search_results = self.search_knowledge_base(comparison_query)
        comparison_data = self.json.loads(search_results)
        
        if "results" in comparison_data:
            comparison = f"Comparison between {product1} and {product2}:\n"
            for result in comparison_data["results"]:
                comparison += f"- {result['name']}: {result['content']}\n"
            return comparison
        else:
            return f"Unable to find direct comparison between {product1} and {product2}."

    def get_policy_details(self, policy_code: str) -> str:
        details_query = f"Policy details for {policy_code}"
        search_results = self.search_knowledge_base(details_query)
        details_data = self.json.loads(search_results)
        
        if "results" in details_data:
            details = f"Policy Details for {policy_code}:\n"
            for result in details_data["results"]:
                details += f"- {result['name']}: {result['content']}\n"
            return details
        else:
            return f"No details found for policy code {policy_code}."

    def explain_term(self, term: str) -> str:
        explanation_query = f"Explain insurance term: {term}"
        search_results = self.search_knowledge_base(explanation_query)
        explanation_data = self.json.loads(search_results)
        
        if "results" in explanation_data:
            explanation = f"Explanation of '{term}':\n"
            for result in explanation_data["results"]:
                explanation += f"{result['content']}\n"
            return explanation
        else:
            return f"No simple explanation found for the term '{term}'."

    def run(
        self,
        message: Optional[Union[List, Dict, str]] = None,
        *,
        stream: bool = True,
        messages: Optional[List[Union[Dict, Message]]] = None,
        **kwargs: Any,
    ) -> Union[Iterator[str], str, Any]:
        if message and isinstance(message, str):
            # Check if the message is asking for a product comparison
            if "compare" in message.lower() and "and" in message.lower():
                products = message.lower().split("compare")[1].split("and")
                product1 = products[0].strip()
                product2 = products[1].strip()
                return self.get_product_comparison(product1, product2)
            
            # Check if the message is asking for policy details
            elif "policy details" in message.lower() or "policy code" in message.lower():
                policy_code = message.split()[-1]  # Assume the policy code is the last word
                return self.get_policy_details(policy_code)
            
            # Check if the message is asking for term explanation
            elif "explain" in message.lower() and "term" in message.lower():
                term = message.split("term")[-1].strip()
                return self.explain_term(term)

        # If no specific handling, use the default run method
        return super().run(message, stream=stream, messages=messages, **kwargs)

    def search_knowledge_base(self, query: str) -> str:
        """Override to add more context to the search results"""
        search_results = super().search_knowledge_base(query)
        results_data = self.json.loads(search_results)
        
        if "results" in results_data:
            enhanced_results = []
            for result in results_data["results"]:
                enhanced_result = result.copy()
                enhanced_result["content"] = self.enhance_content(result["content"])
                enhanced_results.append(enhanced_result)
            
            return self.json.dumps({"results": enhanced_results}, indent=2)
        
        return search_results

    def enhance_content(self, content: str) -> str:
        """Add any call-center specific enhancements to the content"""
        # This is a placeholder. You can add more sophisticated enhancements here.
        return f"[Call Center Note: This information is crucial for customer inquiries] {content}"