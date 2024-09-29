import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from langchain.chat_models import ChatOpenAI
from langgraph.graph import StateGraph, END
from src.backend.services.langgraphs.business_analysis_graph import run_business_analysis_graph
from src.backend.models.models import User
from src.backend.kr8.knowledge.base import AssistantKnowledge
from src.backend.kr8.vectordb.pgvector.pgvector2 import PgVector2
from src.backend.schemas.agile_entity_schemas import AcceptanceCriteria, BusinessAnalysisRequest, BusinessAnalysisResponse, BusinessAnalysisState, ConfluenceSyncRequest, PageSync, QueryResponse, QueryResult, TestCase, UserStory
from src.backend.services.confluence_service import ConfluenceService
from src.backend.helpers.auth import get_current_user
from src.backend.kr8.assistant.assistant_manager import get_assistant_manager, AssistantManager
from src.backend.services.knowledge_base_service import KnowledgeBaseService
from src.backend.db.session import get_db
from src.backend.kr8.assistant.team.business_analyst import EnhancedBusinessAnalyst
from sqlalchemy.orm import Session
import logging 

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

@router.get("/confluence/spaces")
async def get_spaces(
    current_user: User = Depends(get_current_user),
    confluence_service: ConfluenceService = Depends(get_confluence_service)
):
    try:
        spaces = confluence_service.get_spaces()
        return {"spaces": spaces}
    except Exception as e:
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
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confluence/generate_business_analysis")
async def generate_development_artifacts(
    request: BusinessAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    assistant_manager: AssistantManager = Depends(get_assistant_manager),
    confluence_service: ConfluenceService = Depends(get_confluence_service)
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

            documents = confluence_service.get_documents()
            combined_content = "\n\n".join([doc.content for doc in documents])

            initial_state = BusinessAnalysisState(
                business_analysis=combined_content,
                db=db,
                user=current_user,
                assistant=assistant
            )
            logger.info(f"Initial state created with {len(documents)} documents")
            
            async for result in run_business_analysis_graph(initial_state):
                if not result["is_final"]:
                    yield json.dumps(result) + "\n"
                else:
                    final_state = result["graph_state"]
                    
                    # Process the final state
                    if "user_stories" not in final_state or not final_state["user_stories"]:
                        logger.error("User stories not found in final state")
                        yield json.dumps({"error": "User stories not generated"}) + "\n"
                        return

                    if "acceptance_criteria" not in final_state or not final_state["acceptance_criteria"]:
                        logger.error("Acceptance criteria not found in final state")
                        yield json.dumps({"error": "Acceptance criteria not generated"}) + "\n"
                        return

                    if "test_cases" not in final_state or not final_state["test_cases"]:
                        logger.error("Test cases not found in final state")
                        yield json.dumps({"error": "Test cases not generated"}) + "\n"
                        return

                    user_stories = parse_user_stories(final_state["user_stories"])
                    acceptance_criteria = parse_acceptance_criteria(final_state["acceptance_criteria"])
                    test_cases = parse_test_cases(final_state["test_cases"])
                    
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
        raise HTTPException(status_code=500, detail=str(e))
    
def parse_user_stories(user_stories_text: str) -> List[Dict[str, str]]:
    if isinstance(user_stories_text, str):
        # If it's a string, split it into lines and create a list of dictionaries
        stories = user_stories_text.split("\n")
        return [{"story": story.strip()} for story in stories if story.strip()]
    elif isinstance(user_stories_text, list):
        # If it's already a list, ensure each item is a dictionary with a 'story' key
        return [
            story if isinstance(story, dict) and 'story' in story
            else {"story": str(story)}
            for story in user_stories_text
        ]
    else:
        logger.error(f"Unexpected type for user_stories_text: {type(user_stories_text)}")
        return []

def parse_acceptance_criteria(acceptance_criteria_text: str) -> List[AcceptanceCriteria]:
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

def parse_test_cases(test_cases_text: str) -> List[TestCase]:
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