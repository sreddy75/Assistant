# src/backend/kr8/assistant/assistant_manager.py

from fastapi import Depends
from sqlalchemy.orm import Session
from src.backend.kr8.assistant.team.project_management_assistant import ProjectManagementAssistant
from src.backend.services.query_executor import QueryExecutor
from src.backend.services.query_interpreter import QueryInterpreter
from src.backend.db.session import get_db
from src.backend.utils.org_utils import load_org_config
from src.backend.services.azure_devops_service import AzureDevOpsService
from src.backend.models.models import AzureDevOpsConfig, Organization
from src.backend.config.azure_devops_config import is_azure_devops_configured

from typing import Dict, Any, Optional

# Import get_llm_os here instead of from core.assistant
from src.backend.core.assistant import get_llm_os

class AssistantManager:
    def __init__(self):
        self.general_assistants: Dict[int, Any] = {}
        self.pm_assistants: Dict[int, Any] = {}
        self.azure_devops_services: Dict[int, AzureDevOpsService] = {}

    def get_assistant(self, db: Session, user_id: int, org_id: int, user_role: str, user_nickname: str, is_pm_chat: bool = False):
        if is_pm_chat:
            return self._get_pm_assistant(db, user_id, org_id, user_role, user_nickname)
        else:
            return self._get_general_assistant(db, user_id, org_id, user_role, user_nickname)

    def _get_general_assistant(self, db: Session, user_id: int, org_id: int, user_role: str, user_nickname: str):
        if user_id not in self.general_assistants:
            org_config = load_org_config(org_id)
            self.general_assistants[user_id] = self._create_regular_assistant(
                user_id, org_id, user_role, user_nickname, org_config
            )
        return self.general_assistants[user_id]

    def _get_pm_assistant(self, db: Session, user_id: int, org_id: int, user_role: str, user_nickname: str):
        if user_id not in self.pm_assistants:
            org_config = load_org_config(org_id)
            if user_role == "Super Admin" and org_config.get("feature_flags", {}).get("enable_project_management_assistant", False):
                azure_devops_service = self._get_azure_devops_service(db, org_id)
                if azure_devops_service:
                    self.pm_assistants[user_id] = self._create_project_management_assistant(
                        user_id, org_id, user_role, user_nickname, org_config, azure_devops_service
                    )
                else:
                    raise ValueError("Azure DevOps service is not configured for this organization.")
            else:
                raise ValueError("User does not have permission to access the Project Management Assistant.")
        return self.pm_assistants[user_id]

    def get_assistant_by_id(self, assistant_id: int):
        for assistant in list(self.general_assistants.values()) + list(self.pm_assistants.values()):
            if id(assistant) == assistant_id:
                return assistant
        return None

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
        query_interpreter = QueryInterpreter(base_assistant.llm)
        query_executor = QueryExecutor(azure_devops_service)
        
        return ProjectManagementAssistant(
            base_assistant=base_assistant,
            azure_devops_service=azure_devops_service,
            query_interpreter=query_interpreter,
            query_executor=query_executor
        )

    def _get_azure_devops_service(self, db: Session, org_id: int) -> Optional[AzureDevOpsService]:
        if not is_azure_devops_configured():
            return None
        if org_id not in self.azure_devops_services:
            azure_devops_config = db.query(AzureDevOpsConfig).join(Organization).filter(Organization.id == org_id).first()
            if azure_devops_config:
                try:
                    self.azure_devops_services[org_id] = AzureDevOpsService(organization_id=org_id)
                except ValueError:
                    return None
            else:
                return None
        return self.azure_devops_services[org_id]

assistant_manager = AssistantManager()

def get_assistant_manager(db: Session = Depends(get_db)):
    return assistant_manager