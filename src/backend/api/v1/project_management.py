# src/backend/api/project_management.py

from fastapi import APIRouter, Depends, HTTPException
from src.backend.helpers.auth import get_current_user_with_devops_permissions
from src.backend.kr8.assistant.assistant_manager import get_assistant_manager, AssistantManager
from src.backend.schemas.project_management import ProjectManagementQuery, ProjectResponse, TeamResponse
from src.backend.models.models import User
from src.backend.services.azure_devops_service import AzureDevOpsService
from typing import List

router = APIRouter()

def get_azure_devops_service(
    current_user: User = Depends(get_current_user_with_devops_permissions),
    assistant_manager: AssistantManager = Depends(get_assistant_manager)
) -> AzureDevOpsService:
    service = assistant_manager._get_azure_devops_service(current_user.organization_id)
    if not service:
        raise HTTPException(status_code=404, detail="Azure DevOps service not configured for this organization")
    return service

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
    return {"response": response}

@router.get("/projects", response_model=List[ProjectResponse])
async def get_user_projects(
    current_user: User = Depends(get_current_user_with_devops_permissions),
    azure_devops_service: AzureDevOpsService = Depends(get_azure_devops_service)
):
    projects = azure_devops_service.get_projects()
    return [ProjectResponse(id=p.id, name=p.name) for p in projects]

@router.get("/teams", response_model=List[TeamResponse])
async def get_project_teams(
    project_id: str,
    current_user: User = Depends(get_current_user_with_devops_permissions),
    azure_devops_service: AzureDevOpsService = Depends(get_azure_devops_service)
):
    teams = azure_devops_service.get_teams(project_id)
    return [TeamResponse(id=t.id, name=t.name) for t in teams]

