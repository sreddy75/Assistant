# src/backend/api/project_management.py

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.backend.db.session import get_db
from src.backend.helpers.auth import get_current_user_with_devops_permissions
from src.backend.kr8.assistant.assistant_manager import get_assistant_manager, AssistantManager
from src.backend.schemas.project_management import ProjectManagementQuery, ProjectResponse, TeamResponse
from src.backend.models.models import Organization, User
from src.backend.services.azure_devops_service import AzureDevOpsService
from src.backend.config.azure_devops_config import is_azure_devops_configured
from typing import List

router = APIRouter()

logger = logging.getLogger(__name__)

@router.post("/chat")
async def project_management_chat(
    query: ProjectManagementQuery,
    current_user: User = Depends(get_current_user_with_devops_permissions),
    assistant_manager: AssistantManager = Depends(get_assistant_manager)
):
    assistant = assistant_manager.get_assistant(current_user.id, current_user.organization_id, "manager", current_user.nickname)
    if not assistant:
        raise HTTPException(status_code=404, detail="Project Management Assistant not found")

    response = assistant.run(query.query, project=query.project, team=query.team)
    if isinstance(response, list):
        response = "".join(response)
    return {"response": response}

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