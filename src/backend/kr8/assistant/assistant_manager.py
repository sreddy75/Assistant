# src/backend/kr8/assistant/assistant_manager.py

from fastapi import Depends
from sqlalchemy.orm import Session
from src.backend.kr8.assistant.team.business_analyst import EnhancedBusinessAnalyst
from src.frontend.config import settings
from src.backend.kr8.assistant.team.project_management_assistant import ProjectManagementAssistant
from src.backend.db.session import get_db
from src.backend.utils.org_utils import load_org_config
from src.backend.services.azure_devops_service import AzureDevOpsService
from src.backend.models.models import AzureDevOpsConfig, Organization
from src.backend.config.azure_devops_config import is_azure_devops_configured
from src.backend.services.dora_metrics_calculator import DORAMetricsCalculator

from typing import Dict, Any, Optional

from src.backend.core.assistant import get_llm_os

class AssistantManager:
    def __init__(self):
        self.general_assistants: Dict[int, Any] = {}
        self.pm_assistants: Dict[int, Any] = {}
        self.ba_assistants: Dict[int, Any] = {}
        self.azure_devops_services: Dict[int, AzureDevOpsService] = {}

    def get_assistant(self, db: Session, user_id: int, org_id: int, user_role: str, user_nickname: str, assistant_type: str = ""):
        if assistant_type == 'ba':
            return self._get_ba_assistant(db, user_id, org_id, user_role, user_nickname)        
        elif assistant_type == 'pm':
            return self._get_pm_assistant(db, user_id, org_id, user_role, user_nickname)        
        else:
            return self._get_general_assistant(db, user_id, org_id, user_role, user_nickname)

    def _get_general_assistant(self, db: Session, user_id: int, org_id: int, user_role: str, user_nickname: str):
        if user_id not in self.general_assistants:
            org_config = load_org_config(org_id)
            self.general_assistants[user_id] = get_llm_os(
                llm_id="gpt-4o",
                user_id=user_id,
                org_id=org_id,
                user_role=user_role,
                user_nickname=user_nickname,
                debug_mode=True,
                web_search=True,
                org_config=org_config
            )
        return self.general_assistants[user_id]

    def _get_pm_assistant(self, db: Session, user_id: int, org_id: int, user_role: str, user_nickname: str):
        if user_id not in self.pm_assistants:
            org_config = load_org_config(org_id)
            if user_role == "Super Admin" and org_config.get("feature_flags", {}).get("enable_project_management_assistant", False):
                azure_devops_service = self._get_azure_devops_service(db, org_id)
                if azure_devops_service:
                    general_assistant = self._get_general_assistant(db, user_id, org_id, user_role, user_nickname)
                    dora_metrics_calculator = DORAMetricsCalculator(azure_devops_service, db)
                    
                    pm_assistant = ProjectManagementAssistant(
                        azure_devops_service=azure_devops_service,
                        dora_metrics_calculator=dora_metrics_calculator,
                        llm=general_assistant.llm,
                        tools=general_assistant.tools,
                        knowledge_base=general_assistant.knowledge_base,
                        name="Project Management Assistant",
                        role="Analyze DORA metrics and provide project management insights",
                        search_knowledge=True,
                        add_references_to_prompt=True,
                        description="You are an experienced Project Management Assistant specializing in DORA metrics analysis for software development projects. Your role is to provide insights and recommendations based on DORA metrics data.",
                        instructions=[
                            "1. Always start by analyzing the DORA metrics data provided for the project.",
                            "2. Provide insights on deployment frequency, lead time for changes, time to restore service, and change failure rate.",
                            "3. Compare the metrics to industry benchmarks and suggest areas for improvement.",
                            "4. Identify trends in the metrics and their potential impact on project success.",
                            "5. Recommend specific actions to improve the team's performance based on the metrics.",
                            "6. When relevant, search the knowledge base for additional context or historical data.",
                            "7. If any information is unclear or missing, identify what additional details are needed.",
                            "8. Provide clear and actionable advice for project managers and team leads.",
                            "9. When using information from the knowledge base, always cite the source.",
                            "10. If asked about a specific metric, focus on that metric in your response."
                        ],
                        markdown=True,
                        add_datetime_to_instructions=True,
                        debug_mode=settings.DEBUG
                    )
                    
                    # If the general assistant is a ContextAwareAssistant, set the project context
                    if hasattr(general_assistant, 'set_project_context'):
                        pm_assistant.set_project_context = general_assistant.set_project_context
                    
                    self.pm_assistants[user_id] = pm_assistant
                else:
                    raise ValueError("Azure DevOps service is not configured for this organization.")
            else:
                raise ValueError("User does not have permission to access the Project Management Assistant.")
        return self.pm_assistants[user_id]
    
    def _get_ba_assistant(self, db: Session, user_id: int, org_id: int, user_role: str, user_nickname: str):
        if user_id not in self.ba_assistants:
            org_config = load_org_config(org_id)
            if user_role == "Super Admin" and org_config.get("feature_flags", {}).get("enable_business_analyst", False):
                general_assistant = self._get_general_assistant(db, user_id, org_id, user_role, user_nickname)
                ba_assistant = EnhancedBusinessAnalyst(
                    llm=general_assistant.llm,
                    tools=general_assistant.tools,
                    knowledge_base=general_assistant.knowledge_base,
                    debug_mode=settings.DEBUG
                )
                
                # Set additional attributes
                ba_assistant.name = "Agile Business Analyst"
                ba_assistant.role = "Analyze and refine business requirements in an agile software development context"
                ba_assistant.description = "You are an experienced Business Analyst specializing in agile software development projects. Your role is to analyze, refine, and communicate business requirements, ensuring they align with agile principles and practices."
                ba_assistant.instructions = [
                    "1. Begin by thoroughly analyzing the given business requirements or user stories.",
                    "2. Ensure requirements are clear, concise, and follow the INVEST criteria (Independent, Negotiable, Valuable, Estimable, Small, Testable).",
                    "3. Break down large requirements into smaller, manageable user stories when necessary.",
                    "4. Identify and clarify any ambiguities or inconsistencies in the requirements.",
                    "5. Suggest acceptance criteria for each requirement or user story to define 'done'.",
                    "6. Prioritize requirements based on business value and technical feasibility.",
                    "7. Facilitate communication between stakeholders and the development team to ensure shared understanding.",
                    "8. Assist in creating and maintaining product backlogs.",
                    "9. Provide insights on how requirements align with overall product vision and strategy.",
                    "10. Suggest techniques for gathering and validating requirements (e.g., user interviews, surveys, prototyping).",
                    "11. When relevant, search the knowledge base for additional context or historical data.",
                    "12. If any information is unclear or missing, identify what additional details are needed.",
                    "13. Offer recommendations for requirement refinement and backlog grooming processes.",
                    "14. When using information from the knowledge base, always cite the source.",
                    "15. If asked about a specific agile practice or requirement technique, focus on that in your response."
                ]
                ba_assistant.markdown = True
                ba_assistant.add_datetime_to_instructions = True
                
                # If the general assistant is a ContextAwareAssistant, set the project context
                if hasattr(general_assistant, 'set_project_context'):
                    ba_assistant.set_project_context = general_assistant.set_project_context
                
                self.ba_assistants[user_id] = ba_assistant
            else:
                raise ValueError("User does not have permission to access the Business Analyst Assistant.")
        return self.ba_assistants[user_id]

    def get_assistant_by_id(self, assistant_id: int):
        for assistant in list(self.general_assistants.values()) + list(self.pm_assistants.values()):
            if id(assistant) == assistant_id:
                return assistant
        return None

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