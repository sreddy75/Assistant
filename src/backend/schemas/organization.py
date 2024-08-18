
from pydantic import BaseModel


class OrganizationCreate(BaseModel):
    name: str
    roles: list
    assistants: dict
    feature_flags: dict

class OrganizationUpdate(BaseModel):
    roles: list = None
    assistants: dict = None
    feature_flags: dict = None