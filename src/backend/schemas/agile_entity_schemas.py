from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.backend.kr8.assistant.team.business_analyst import EnhancedBusinessAnalyst
from src.backend.models.models import User


class BusinessAnalysisRequest(BaseModel):
    org_id: int
    task: str

class UserStory(BaseModel):
    story: str

class AcceptanceCriteria(BaseModel):
    user_story: str
    criteria: List[str]

class TestCase(BaseModel):
    name: str
    steps: List[str]
    expected_result: str

class BusinessAnalysisResponse(BaseModel):
    user_stories: List[UserStory]
    acceptance_criteria: List[AcceptanceCriteria]
    test_cases: List[TestCase]  # Changed from technical_considerations to test_cases
    graph_state: Dict[str, str] 

    
class BusinessAnalysisState(BaseModel):
    business_analysis: Optional[str] = None
    key_requirements: Optional[str] = None
    user_stories: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    test_cases: Optional[str] = None
    db: Optional[Session] = None
    user: Optional[User] = None
    assistant: Optional[EnhancedBusinessAnalyst] = None

    class Config:
        arbitrary_types_allowed = True
    
class QueryResult(BaseModel):
    id: str
    name: str
    content: str
    url: str
    relevance: float
    
class QueryResponse(BaseModel):
    results: List[QueryResult]
        
class ConfluenceSyncRequest(BaseModel):
    org_id: int = Field(..., description="The ID of the organization")
    space_key: str = Field(..., description="The key of the Confluence space to sync")

    class Config:
        schema_extra = {
            "example": {
                "org_id": 1,
                "space_key": "CTM"
            }
        }    
        
class PageSync(BaseModel):
    space_key: str
    page_ids: List[str]