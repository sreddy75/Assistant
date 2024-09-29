# src/backend/services/langgraphs/business_analysis_graph.py

import logging
from typing import Any, AsyncGenerator, Dict, List
from langchain.chat_models import ChatOpenAI
from langgraph.graph import StateGraph, END
from src.backend.schemas.agile_entity_schemas import BusinessAnalysisState
from src.backend.services.confluence_service import ConfluenceService
from src.backend.kr8.assistant.team.business_analyst import EnhancedBusinessAnalyst

logger = logging.getLogger(__name__)

def create_business_analysis_graph():
    def analyze_business_documents(state: BusinessAnalysisState) -> BusinessAnalysisState:
        logger.info("Starting analyze_business_documents")
        if state.db is None or state.user is None:
            raise ValueError("Database session or user not found in state")
        confluence_service = ConfluenceService(state.db, state.user)
        documents = confluence_service.get_documents()
        logger.info(f"Retrieved {len(documents)} documents")
        combined_content = "\n\n".join([doc.content for doc in documents])
        state.business_analysis = combined_content
        logger.info(f"Combined content length: {len(combined_content)}")
        return state

    def extract_key_requirements(state: BusinessAnalysisState) -> BusinessAnalysisState:
        logger.info("Starting extract_key_requirements")
        if state.assistant is None:
            raise ValueError("Assistant not found in state")
        result = state.assistant.run(f"Based on the following business analysis, extract the key requirements:\n\n{state.business_analysis}")
        state.key_requirements = result
        logger.info(f"Extracted key requirements: {result[:100]}...")
        return state

    def generate_user_stories(state: BusinessAnalysisState) -> BusinessAnalysisState:
        logger.info("Starting generate_user_stories")
        if state.assistant is None:
            raise ValueError("Assistant not found in state")
        result = state.assistant.run(f"Create user stories based on these key requirements:\n\n{state.key_requirements}")
        state.user_stories = result
        logger.info(f"Generated user stories: {result[:100]}...")
        return state

    def create_acceptance_criteria(state: BusinessAnalysisState) -> BusinessAnalysisState:
        logger.info("Starting create_acceptance_criteria")
        if state.assistant is None:
            raise ValueError("Assistant not found in state")
        result = state.assistant.run(f"Create acceptance criteria for each of these user stories:\n\n{state.user_stories}")
        state.acceptance_criteria = result
        logger.info(f"Created acceptance criteria: {result[:100]}...")
        return state

    def generate_test_cases(state: BusinessAnalysisState) -> BusinessAnalysisState:
        logger.info("Starting generate_test_cases")
        if state.assistant is None:
            raise ValueError("Assistant not found in state")
        result = state.assistant.run(f"Generate test cases based on these user stories and acceptance criteria:\n\nUser Stories:\n{state.user_stories}\n\nAcceptance Criteria:\n{state.acceptance_criteria}")
        state.test_cases = result
        logger.info(f"Generated test cases: {result[:100]}...")
        return state

    workflow = StateGraph(state_schema=BusinessAnalysisState)

    workflow.add_node("AnalyzeBusinessDocuments", analyze_business_documents)
    workflow.add_node("ExtractKeyRequirements", extract_key_requirements)
    workflow.add_node("GenerateUserStories", generate_user_stories)
    workflow.add_node("CreateAcceptanceCriteria", create_acceptance_criteria)
    workflow.add_node("GenerateTestCases", generate_test_cases)

    workflow.add_edge("AnalyzeBusinessDocuments", "ExtractKeyRequirements")
    workflow.add_edge("ExtractKeyRequirements", "GenerateUserStories")
    workflow.add_edge("GenerateUserStories", "CreateAcceptanceCriteria")
    workflow.add_edge("CreateAcceptanceCriteria", "GenerateTestCases")
    workflow.add_edge("GenerateTestCases", END)

    workflow.set_entry_point("AnalyzeBusinessDocuments")

    return workflow.compile()

async def run_business_analysis_graph(initial_state: BusinessAnalysisState) -> AsyncGenerator[Dict[str, Any], None]:
    graph = create_business_analysis_graph()
    current_state = initial_state
    
    # Define node_to_attr outside the loop
    node_to_attr = {
        "AnalyzeBusinessDocuments": "business_analysis",
        "ExtractKeyRequirements": "key_requirements",
        "GenerateUserStories": "user_stories",
        "CreateAcceptanceCriteria": "acceptance_criteria",
        "GenerateTestCases": "test_cases"
    }
    
    async for event in graph.astream(initial_state):
        if isinstance(event, dict):
            for node, state in event.items():
                if isinstance(state, BusinessAnalysisState):
                    current_state = state
                    logger.info(f"Node {node} completed. State keys: {state.dict().keys()}")
                    
                    attr_name = node_to_attr.get(node)
                    if attr_name:
                        response = getattr(state, attr_name, "")
                        logger.info(f"Response for {node} (attribute {attr_name}): {response[:100]}...")
                        yield {
                            "graph_state": {attr_name: response},
                            "response": response,
                            "is_final": False
                        }
                    else:
                        logger.warning(f"Unknown node: {node}")
                elif isinstance(state, dict):
                    logger.info(f"Node {node} completed. State keys: {state.keys()}")
                    current_state = BusinessAnalysisState(**state)
                    attr_name = node_to_attr.get(node, node)
                    response = state.get(attr_name, "")
                    logger.info(f"Response for {node} (attribute {attr_name}): {response[:100]}...")
                    yield {
                        "graph_state": {attr_name: response},
                        "response": response,
                        "is_final": False
                    }
                else:
                    logger.warning(f"Unexpected state type for node {node}: {type(state)}")
        else:
            logger.warning(f"Unexpected event type: {type(event)}")
    
    # Yield the final state
    final_state = current_state.dict(exclude={'db', 'user', 'assistant'})
    logger.info(f"Final state: {final_state}")
    yield {
        "graph_state": final_state,
        "response": "Business analysis completed",
        "is_final": True
    }