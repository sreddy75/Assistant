import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from src.backend.models.models import User
from src.backend.kr8.knowledge.base import AssistantKnowledge
from src.backend.kr8.vectordb.pgvector.pgvector2 import PgVector2
from src.backend.schemas.agile_entity_schemas import (
    AcceptanceCriteria, BusinessAnalysisChatRequest, BusinessAnalysisRequest, 
    BusinessAnalysisResponse, BusinessAnalysisState, ConfluenceSyncRequest, 
    PageSync, QueryResponse, QueryResult, TestCase, UserStory
)
from src.backend.services.confluence_service import ConfluenceService
from src.backend.helpers.auth import get_current_user
from src.backend.kr8.assistant.assistant_manager import get_assistant_manager, AssistantManager
from src.backend.services.knowledge_base_service import KnowledgeBaseService
from src.backend.db.session import get_db
from src.backend.kr8.assistant.team.business_analyst import EnhancedBusinessAnalyst
from src.backend.services.langgraphs.business_analysis_graph import BusinessAnalysisGraph

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_confluence_service(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ConfluenceService:
    return ConfluenceService(db, current_user)

def get_knowledge_base(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> AssistantKnowledge:
    return AssistantKnowledge(
        vector_db=PgVector2(
            collection="confluence_pages",
            db_url=db.bind.url,
            user_id=current_user.id,
            org_id=current_user.organization_id
        )
    )

class AgileTeam:
    @router.get("/confluence/spaces")
    async def get_spaces(
        current_user: User = Depends(get_current_user),
        confluence_service: ConfluenceService = Depends(get_confluence_service)
    ):
        try:
            spaces = confluence_service.get_spaces()
            return {"spaces": spaces}
        except Exception as e:
            logger.error(f"Error in get_spaces: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/confluence/pages/{space_key}")
    async def get_pages(
        space_key: str,
        current_user: User = Depends(get_current_user),
        confluence_service: ConfluenceService = Depends(get_confluence_service)
    ):
        try:
            pages = confluence_service.get_pages_in_space(space_key)
            return {"pages": pages}
        except Exception as e:
            logger.error(f"Error in get_pages: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/confluence/sync")
    async def sync_pages(
        request: PageSync,
        current_user: User = Depends(get_current_user),
        confluence_service: ConfluenceService = Depends(get_confluence_service)
    ):
        try:
            result = await confluence_service.sync_selected_pages(request.space_key, request.page_ids)
            return {"success": True, "message": "Selected pages synchronized successfully", "result": result}
        except Exception as e:
            logger.error(f"Error in sync_pages: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    @router.post("/confluence/generate_business_analysis")
    async def generate_development_artifacts(
        request: BusinessAnalysisRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        assistant_manager: AssistantManager = Depends(get_assistant_manager),
        confluence_service: ConfluenceService = Depends(get_confluence_service),
        analysis_id: Optional[str] = Query(None)
    ):
        logger.info(f"Starting generate_development_artifacts for user {current_user.id}")
        
        async def generate():
            try:
                assistant = assistant_manager.get_assistant(
                    db=db,
                    user_id=current_user.id,
                    org_id=current_user.organization_id,
                    user_role=current_user.role,
                    user_nickname=current_user.nickname,
                    assistant_type="ba"
                )
                logger.info(f"Assistant created: {type(assistant)}")
                
                if not isinstance(assistant, EnhancedBusinessAnalyst):
                    raise ValueError("Invalid assistant type for business analysis")

                graph = BusinessAnalysisGraph(db, current_user, assistant, analysis_id)
                
                async for result in graph.run_business_analysis_graph():
                    logger.info(f"Received result from business_analysis_graph: {result}")
                    yield json.dumps(result) + "\n"

                    if result.get("is_final", False):
                        final_state = result["graph_state"]
                        logger.info(f"Final state received: {final_state}")
                        
                        user_stories = AgileTeam.parse_user_stories(final_state.get("user_stories", ""))
                        acceptance_criteria = AgileTeam.parse_acceptance_criteria(final_state.get("acceptance_criteria", ""))
                        test_cases = AgileTeam.parse_test_cases(final_state.get("test_cases", ""))
                        
                        final_response = BusinessAnalysisResponse(
                            user_stories=[UserStory(**story) if isinstance(story, dict) else UserStory(story=str(story)) for story in user_stories],
                            acceptance_criteria=acceptance_criteria,
                            test_cases=test_cases,
                            graph_state=final_state
                        )
                        
                        logger.info("Sending final response")
                        yield json.dumps(final_response.dict()) + "\n"

            except Exception as e:
                logger.error(f"Error in generate_development_artifacts: {str(e)}", exc_info=True)
                yield json.dumps({"error": str(e)}) + "\n"

        logger.info("Returning StreamingResponse")
        return StreamingResponse(generate(), media_type="application/json")

    @router.post("/business-analysis/chat")
    async def chat_with_analysis_results(
        request: BusinessAnalysisChatRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        assistant_manager: AssistantManager = Depends(get_assistant_manager),
        knowledge_base: AssistantKnowledge = Depends(get_knowledge_base)
    ):
        logger.info(f"Starting chat_with_analysis_results for user {current_user.id}")
        
        async def generate_response():
            try:
                assistant = assistant_manager.get_assistant(
                    db=db,
                    user_id=current_user.id,
                    org_id=request.org_id,
                    user_role=current_user.role,
                    user_nickname=current_user.nickname,
                    assistant_type="ba"
                )
                logger.info(f"Assistant created: {type(assistant)}")
                
                if not isinstance(assistant, EnhancedBusinessAnalyst):
                    raise ValueError("Invalid assistant type for business analysis chat")

                documents = knowledge_base.search(request.query)
                logger.info(f"Retrieved {len(documents)} relevant documents")

                context = "\n\n".join([doc.content for doc in documents])
                
                for key, value in request.context.items():
                    context += f"\n\n{key.replace('_', ' ').title()}:\n{value}"

                response = assistant.generate_response(request.query, context)
                if not response.strip():
                    raise ValueError("Received empty response from assistant")
                logger.info("Response generated successfully")

                yield json.dumps({"response": response}) + "\n"

            except Exception as e:
                logger.error(f"Error in chat_with_analysis_results: {str(e)}", exc_info=True)
                yield json.dumps({"error": str(e)}) + "\n"

        logger.info("Returning StreamingResponse")
        return StreamingResponse(generate_response(), media_type="application/json")

    @router.get("/confluence/query", response_model=QueryResponse)
    async def query_knowledge_base(
        query: str,
        current_user: User = Depends(get_current_user),
        knowledge_base: AssistantKnowledge = Depends(get_knowledge_base)
    ):
        try:
            documents = knowledge_base.search(query)
            results = [
                QueryResult(
                    id=doc.id,
                    name=doc.name,
                    content=doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                    url=doc.meta_data.get("url", ""),
                    relevance=doc.meta_data.get("relevance", 0.0)
                )
                for doc in documents
            ]
            return QueryResponse(results=results)
        except Exception as e:
            logger.error(f"Error in query_knowledge_base: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    def parse_user_stories(user_stories_text: str) -> List[Dict[str, str]]:
        if not user_stories_text:
            return []
        if isinstance(user_stories_text, str):
            stories = user_stories_text.split("\n")
            return [{"story": story.strip()} for story in stories if story.strip()]
        elif isinstance(user_stories_text, list):
            return [
                story if isinstance(story, dict) and 'story' in story
                else {"story": str(story)}
                for story in user_stories_text
            ]
        else:
            logger.error(f"Unexpected type for user_stories_text: {type(user_stories_text)}")
            return []

    @staticmethod
    def parse_acceptance_criteria(acceptance_criteria_text: str) -> List[AcceptanceCriteria]:
        if not acceptance_criteria_text:
            return []
        criteria_blocks = acceptance_criteria_text.split("\n\n")
        result = []
        for block in criteria_blocks:
            lines = block.split("\n")
            if lines:
                result.append(AcceptanceCriteria(
                    user_story=lines[0].strip(),
                    criteria=[line.strip() for line in lines[1:] if line.strip()]
                ))
        return result

    @staticmethod
    def parse_test_cases(test_cases_text: str) -> List[TestCase]:
        if not test_cases_text:
            return []
        test_cases = []
        current_test_case = None

        for line in test_cases_text.split('\n'):
            line = line.strip()
            if line.startswith("Test Case:"):
                if current_test_case:
                    test_cases.append(TestCase(**current_test_case))
                current_test_case = {"name": line[10:].strip(), "steps": [], "expected_result": ""}
            elif line.startswith("Step ") and current_test_case:
                current_test_case["steps"].append(line)
            elif line.startswith("Expected Result:") and current_test_case:
                current_test_case["expected_result"] = line[17:].strip()

        if current_test_case:
            test_cases.append(TestCase(**current_test_case))

        return test_cases