# File: project_management.py

import json
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from src.backend.kr8.assistant.assistant_manager import AssistantManager, get_assistant_manager
from src.backend.core.config import settings
from src.backend.services.azure_devops_service import AzureDevOpsService
from src.backend.kr8.assistant.team.project_management_assistant import ProjectManagementAssistant
from src.backend.config.azure_devops_config import is_azure_devops_configured
from src.backend.db.session import get_db
from src.backend.helpers.auth import get_current_active_user
from src.backend.models.models import User

router = APIRouter()
logger = logging.getLogger(__name__)

def get_current_organization_id(current_user: User = Depends(get_current_active_user)) -> int:
    return current_user.organization_id

def get_azure_devops_service(org_id: int = Depends(get_current_organization_id)):
    if not is_azure_devops_configured():
        raise HTTPException(status_code=500, detail="Azure DevOps is not configured for this organization")
    return AzureDevOpsService(org_id)

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's message")
    project: str = Field(..., description="The project ID")
    team: str = Field(..., description="The team ID")
    org_id: Optional[int] = Field(None, description="The organization ID")

@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    assistant_manager: AssistantManager = Depends(get_assistant_manager),
):
    try:
        logger.info(f"Received chat request: {request.dict()}")

        assistant = assistant_manager._get_pm_assistant(db, current_user.id, request.org_id or current_user.organization_id, current_user.role, current_user.nickname)

        async def stream_response():
            try:
                response = assistant.run(request.message, project_id=request.project, team_id=request.team, stream=True)
                
                buffer = ""
                chunk_size = 20  # Adjust this value to control streaming speed (larger value = faster)
                delay = 0.05  # Adjust this value to control delay between chunks (smaller value = faster)
                
                for chunk in response:
                    buffer += chunk
                    while len(buffer) >= chunk_size:
                        yield json.dumps({"response": buffer[:chunk_size]}) + "\n"
                        buffer = buffer[chunk_size:]
                        await asyncio.sleep(delay)
                
                if buffer:  # Yield any remaining content in the buffer
                    yield json.dumps({"response": buffer}) + "\n"
                
            except Exception as e:
                logger.error(f"Error in stream_response: {str(e)}", exc_info=True)
                error_message = f"An error occurred while processing your request: {str(e)}"
                yield json.dumps({"error": error_message}) + "\n"

        return StreamingResponse(stream_response(), media_type="application/json")
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": f"An unexpected error occurred: {str(e)}"})
        
@router.get("/projects")
async def get_user_projects(
    azure_devops_service: AzureDevOpsService = Depends(get_azure_devops_service)
):
    projects = azure_devops_service.get_projects()
    return [{"id": p.id, "name": p.name} for p in projects]

@router.get("/teams")
async def get_project_teams(
    project_id: str,
    azure_devops_service: AzureDevOpsService = Depends(get_azure_devops_service)
):
    teams = azure_devops_service.get_teams(project_id)
    return [{"id": t.id, "name": t.name} for t in teams]