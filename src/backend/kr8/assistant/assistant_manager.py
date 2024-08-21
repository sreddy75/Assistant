from fastapi import Depends
from sqlalchemy.orm import Session
from src.backend.db.session import get_db
from src.backend.utils.org_utils import load_org_config
from src.backend.core.assistant import get_llm_os

class AssistantManager:
    def __init__(self, db: Session):
        self.db = db
        self.assistants = {}

    def get_assistant(self, user_id: int, org_id: int, user_role: str, user_nickname: str):
        if user_id not in self.assistants:
            org_config = load_org_config(org_id)
            llm_os = get_llm_os(
                llm_id="gpt-4o",
                user_id=user_id,
                org_id=org_id,
                user_role=user_role,
                user_nickname=user_nickname,
                debug_mode=True,
                web_search=True,
                db=self.db,
                org_config=org_config
            )
            self.assistants[user_id] = llm_os
        return self.assistants[user_id]

    def get_assistant_by_id(self, assistant_id: int):
        return next((assistant for assistant in self.assistants.values() if id(assistant) == assistant_id), None)

assistant_manager = AssistantManager(Depends(get_db))

def get_assistant_manager():
    return assistant_manager