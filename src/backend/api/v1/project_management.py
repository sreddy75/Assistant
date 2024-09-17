import json
import asyncio
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from src.backend.kr8.assistant.team.project_management_assistant import ProjectManagementAssistant
from src.backend.config.azure_devops_config import is_azure_devops_configured
from src.backend.services.azure_devops_service import AzureDevOpsService
from src.backend.db.session import get_db
from src.backend.helpers.auth import get_current_active_user
from src.backend.kr8.assistant.assistant_manager import get_assistant_manager, AssistantManager
from src.backend.models.models import User
from typing import Optional

router = APIRouter()

@router.post("/chat")
async def chat(
    message: str = Body(...),
    project: Optional[str] = Body(None),
    team: Optional[str] = Body(None),
    is_pm_chat: bool = Body(True),
    assistant_id: Optional[int] = Query(None),
    assistant_manager: AssistantManager = Depends(get_assistant_manager),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        assistant = assistant_manager.get_assistant(
            db=db,
            user_id=current_user.id,
            org_id=current_user.organization_id,
            user_role=current_user.role,
            user_nickname=current_user.nickname,
            is_pm_chat=is_pm_chat
        )

        if not project or not team:
            raise HTTPException(status_code=400, detail="Project and team must be provided for PM chat")

        async def stream_response():
            try:
                previous_response = ""
                for chunk in assistant.run(message, project=project, team=team, stream=True):
                    if chunk:  # Only process non-empty chunks
                        current_response = previous_response + chunk
                        yield (json.dumps({"response": current_response, "delta": chunk}) + "\n").encode('utf-8')
                        previous_response = current_response
                    await asyncio.sleep(0)
            except Exception as e:
                yield (json.dumps({"error": str(e)}) + "\n").encode('utf-8')

        return StreamingResponse(stream_response(), media_type="application/json")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

def get_azure_devops_service(org_id: int) -> AzureDevOpsService:
    if not is_azure_devops_configured():
        raise HTTPException(status_code=500, detail="Azure DevOps is not configured for this organization")
    
    try:
        return AzureDevOpsService(org_id)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects")
async def get_user_projects(org_id: int):
    azure_devops_service = get_azure_devops_service(org_id)
    projects = azure_devops_service.get_projects()
    return [{"id": p.id, "name": p.name} for p in projects]

@router.get("/teams")
async def get_project_teams(org_id: int, project_id: str):
    azure_devops_service = get_azure_devops_service(org_id)
    teams = azure_devops_service.get_teams(project_id)
    return [{"id": t.id, "name": t.name} for t in teams]

@router.get("/dora-metrics/{project_id}/{team_id}")
async def get_dora_metrics(
    project_id: str,
    team_id: str,
    query: str,
    org_id: int,
    assistant_manager: AssistantManager = Depends(get_assistant_manager),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        assistant = assistant_manager.get_assistant(
            db=db,
            user_id=current_user.id,
            org_id=current_user.organization_id,
            user_role=current_user.role,
            user_nickname=current_user.nickname,
            is_pm_chat=True
        )

        if not isinstance(assistant, ProjectManagementAssistant):
            raise HTTPException(status_code=400, detail="Invalid assistant type for DORA metrics query")

        result = assistant.get_dora_metrics(project_id, team_id, query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")