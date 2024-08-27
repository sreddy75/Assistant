from typing import Dict
from pydantic import BaseModel


class ProjectLoadRequest(BaseModel):
    assistant_id: int
    project_name: str
    project_type: str
    directory_content: Dict[str, str]