# src/backend/kr8/assistant/assistant_manager.py

from fastapi import Depends
from sqlalchemy.orm import Session
from src.backend.db.session import get_db
from src.backend.utils.org_utils import load_org_config
from src.backend.core.assistant import get_llm_os
from src.backend.kr8.assistant.team.project_management_assistant import ProjectManagementAssistant
from src.backend.services.azure_devops_service import AzureDevOpsService
from src.backend.models.models import AzureDevOpsConfig, Organization
from src.backend.config.azure_devops_config import is_azure_devops_configured

from typing import Dict, Any, Optional

class AssistantManager:
    def __init__(self, db: Session):
        self.db = db
        self.assistants: Dict[int, Any] = {}
        self.azure_devops_services: Dict[int, AzureDevOpsService] = {}

    def _get_azure_devops_service(self, org_id: int) -> Optional[AzureDevOpsService]:
        if not is_azure_devops_configured():
            return None
        if org_id not in self.azure_devops_services:
            azure_devops_config = self.db.query(AzureDevOpsConfig).join(Organization).filter(Organization.id == org_id).first()
            if azure_devops_config:
                try:
                    self.azure_devops_services[org_id] = AzureDevOpsService(organization_id=org_id)
                except ValueError:
                    return None
            else:
                return None
        return self.azure_devops_services[org_id]
    
    def get_assistant(self, user_id: int, org_id: int, user_role: str, user_nickname: str):
        if user_id not in self.assistants:
            org_config = load_org_config(org_id)
            
            if user_role == "manager" and org_config.get("feature_flags", {}).get("enable_project_management_assistant", False):
                azure_devops_service = self._get_azure_devops_service(org_id)
                if azure_devops_service:
                    self.assistants[user_id] = self._create_project_management_assistant(
                        user_id, org_id, user_role, user_nickname, org_config, azure_devops_service
                    )
                else:
                    # Fallback to regular assistant if Azure DevOps is not configured
                    self.assistants[user_id] = self._create_regular_assistant(
                        user_id, org_id, user_role, user_nickname, org_config
                    )
            else:
                self.assistants[user_id] = self._create_regular_assistant(
                    user_id, org_id, user_role, user_nickname, org_config
                )

        return self.assistants[user_id]

    def get_assistant_by_id(self, assistant_id: int):
        return next((assistant for assistant in self.assistants.values() if id(assistant) == assistant_id), None)

    def _create_regular_assistant(self, user_id: int, org_id: int, user_role: str, user_nickname: str, org_config: Dict[str, Any]):
        return get_llm_os(
            llm_id="gpt-4o",
            user_id=user_id,
            org_id=org_id,
            user_role=user_role,
            user_nickname=user_nickname,
            debug_mode=True,
            web_search=True,
            org_config=org_config
        )

    def _create_project_management_assistant(self, user_id: int, org_id: int, user_role: str, user_nickname: str, org_config: Dict[str, Any], azure_devops_service: AzureDevOpsService):
        base_assistant = self._create_regular_assistant(user_id, org_id, user_role, user_nickname, org_config)
        return ProjectManagementAssistant(
            base_assistant=base_assistant,
            azure_devops_service=azure_devops_service
        )

    def _get_azure_devops_service(self, org_id: int) -> AzureDevOpsService:
        if org_id not in self.azure_devops_services:
            azure_devops_config = self.db.query(AzureDevOpsConfig).join(Organization).filter(Organization.id == org_id).first()
            if azure_devops_config:
                self.azure_devops_services[org_id] = AzureDevOpsService(
                    org_url=azure_devops_config.organization_url,
                    personal_access_token=azure_devops_config.personal_access_token,
                    organization_id=org_id
                )
            else:
                return None
        return self.azure_devops_services[org_id]

assistant_manager = AssistantManager(Depends(get_db))

def get_assistant_manager():
    return assistant_manager