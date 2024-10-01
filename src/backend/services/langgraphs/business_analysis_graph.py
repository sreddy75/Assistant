# src/backend/services/langgraphs/business_analysis_graph.py

import logging
import uuid
from typing import Any, AsyncGenerator, Dict, List
from langchain.chat_models import ChatOpenAI
from langgraph.graph import StateGraph, END
from src.backend.schemas.agile_entity_schemas import BusinessAnalysisState
from src.backend.services.confluence_service import ConfluenceService
from src.backend.kr8.assistant.team.business_analyst import EnhancedBusinessAnalyst
from src.backend.kr8.vectordb.pgvector.pgvector2 import PgVector2
from src.backend.kr8.document.base import Document 
from src.backend.kr8.knowledge.base import AssistantKnowledge

logger = logging.getLogger(__name__)

class BusinessAnalysisGraph:
    def __init__(self, db, user, assistant):
        self.db = db
        self.user = user
        self.assistant = assistant
        self.vector_db = PgVector2(
            collection="confluence_pages",
            db_url=db.bind.url,
            user_id=user.id,
            org_id=user.organization_id
        )
        self.knowledge_base = AssistantKnowledge(vector_db=self.vector_db)
        self.confluence_service = ConfluenceService(db, user)
        self.analysis_id = str(uuid.uuid4())

    def analyze_business_documents(self, state: BusinessAnalysisState) -> BusinessAnalysisState:
        logger.info("Starting analyze_business_documents")
        documents = self.confluence_service.get_documents()
        logger.info(f"Retrieved {len(documents)} documents")
        combined_content = "\n\n".join([doc.content for doc in documents])
        state.business_analysis = combined_content
        logger.info(f"Combined content length: {len(combined_content)}")
        return state

    def extract_key_requirements(self, state: BusinessAnalysisState) -> BusinessAnalysisState:
        logger.info("Starting extract_key_requirements")
        result = self.assistant.run(f"Based on the following business analysis, extract the key requirements:\n\n{state.business_analysis}")
        state.key_requirements = result
        logger.info(f"Extracted key requirements: {result[:100]}...")
        return state

    def generate_user_stories(self, state: BusinessAnalysisState) -> BusinessAnalysisState:
        logger.info("Starting generate_user_stories")
        result = self.assistant.run(f"Create user stories based on these key requirements:\n\n{state.key_requirements}")
        state.user_stories = result
        logger.info(f"Generated user stories: {result[:100]}...")
        return state

    def create_acceptance_criteria(self, state: BusinessAnalysisState) -> BusinessAnalysisState:
        logger.info("Starting create_acceptance_criteria")
        result = self.assistant.run(f"Create acceptance criteria for each of these user stories:\n\n{state.user_stories}")
        state.acceptance_criteria = result
        logger.info(f"Created acceptance criteria: {result[:100]}...")
        return state

    def generate_test_cases(self, state: BusinessAnalysisState) -> BusinessAnalysisState:
        logger.info("Starting generate_test_cases")
        result = self.assistant.run(f"Generate test cases based on these user stories and acceptance criteria:\n\nUser Stories:\n{state.user_stories}\n\nAcceptance Criteria:\n{state.acceptance_criteria}")
        state.test_cases = result
        logger.info(f"Generated test cases: {result[:100]}...")
        return state

    def store_interim_results(self, state: BusinessAnalysisState) -> BusinessAnalysisState:
        logger.info("Storing interim results in pgvector")
        for key, value in state.dict().items():
            if key not in ['db', 'user', 'assistant'] and value:
                unique_id = f"ba_result_{key}_{self.analysis_id}"
                try:
                    document = Document(
                        id=unique_id,
                        name=f"Business Analysis Result: {key.replace('_', ' ').title()}",
                        content=str(value),
                        meta_data={
                            "type": "business_analysis_result",
                            "step": key,
                            "analysis_id": self.analysis_id,
                            "user_id": self.user.id,
                            "org_id": self.user.organization_id,
                            "url": f"/business-analysis/{self.analysis_id}/{key}"
                        }
                    )
                    logger.debug(f"Created document: {document}")
                    self.knowledge_base.load_document(document)
                    logger.info(f"Successfully stored interim result for {key}")
                except Exception as e:
                    logger.error(f"Error creating or storing document for {key}: {str(e)}", exc_info=True)
        logger.info("Interim results storage attempt completed")
        return state

    def create_graph(self):
        workflow = StateGraph(state_schema=BusinessAnalysisState)

        workflow.add_node("AnalyzeBusinessDocuments", self.analyze_business_documents)
        workflow.add_node("StoreAnalysis", self.store_interim_results)
        workflow.add_node("ExtractKeyRequirements", self.extract_key_requirements)
        workflow.add_node("StoreRequirements", self.store_interim_results)
        workflow.add_node("GenerateUserStories", self.generate_user_stories)
        workflow.add_node("StoreUserStories", self.store_interim_results)
        workflow.add_node("CreateAcceptanceCriteria", self.create_acceptance_criteria)
        workflow.add_node("StoreAcceptanceCriteria", self.store_interim_results)
        workflow.add_node("GenerateTestCases", self.generate_test_cases)
        workflow.add_node("StoreTestCases", self.store_interim_results)

        workflow.add_edge("AnalyzeBusinessDocuments", "StoreAnalysis")
        workflow.add_edge("StoreAnalysis", "ExtractKeyRequirements")
        workflow.add_edge("ExtractKeyRequirements", "StoreRequirements")
        workflow.add_edge("StoreRequirements", "GenerateUserStories")
        workflow.add_edge("GenerateUserStories", "StoreUserStories")
        workflow.add_edge("StoreUserStories", "CreateAcceptanceCriteria")
        workflow.add_edge("CreateAcceptanceCriteria", "StoreAcceptanceCriteria")
        workflow.add_edge("StoreAcceptanceCriteria", "GenerateTestCases")
        workflow.add_edge("GenerateTestCases", "StoreTestCases")
        workflow.add_edge("StoreTestCases", END)

        workflow.set_entry_point("AnalyzeBusinessDocuments")

        return workflow.compile()

    async def run_business_analysis_graph(self) -> AsyncGenerator[Dict[str, Any], None]:
        graph = self.create_graph()
        initial_state = BusinessAnalysisState(
            db=self.db,
            user=self.user,
            assistant=self.assistant,
            analysis_id=self.analysis_id
        )
        
        node_to_attr = {
            "AnalyzeBusinessDocuments": "business_analysis",
            "ExtractKeyRequirements": "key_requirements",
            "GenerateUserStories": "user_stories",
            "CreateAcceptanceCriteria": "acceptance_criteria",
            "GenerateTestCases": "test_cases"
        }
        
        try:
            async for event in graph.astream(initial_state):
                if isinstance(event, dict):
                    for node, state in event.items():
                        if isinstance(state, BusinessAnalysisState):
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
                            elif node.startswith("Store"):
                                logger.info(f"Interim results stored for {node}")
                            else:
                                logger.warning(f"Unknown node: {node}")
                        elif isinstance(state, dict):
                            logger.info(f"Node {node} completed. State keys: {state.keys()}")
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
            final_state = initial_state.dict(exclude={'db', 'user', 'assistant'})
            logger.info(f"Final state: {final_state}")
            yield {
                "graph_state": final_state,
                "response": "Business analysis completed",
                "is_final": True
            }
        except Exception as e:
            logger.error(f"Error during graph execution: {str(e)}", exc_info=True)
            yield {
                "graph_state": initial_state.dict(exclude={'db', 'user', 'assistant'}),
                "response": f"Error during business analysis: {str(e)}",
                "is_final": True,
                "error": str(e)
            }