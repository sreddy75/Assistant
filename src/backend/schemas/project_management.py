# Azure DevOps related schemas
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class AzureDevOpsConfigBase(BaseModel):
    organization_url: str
    personal_access_token: str

class AzureDevOpsConfigCreate(AzureDevOpsConfigBase):
    organization_id: int

class AzureDevOpsConfigUpdate(BaseModel):
    organization_url: Optional[str] = None
    personal_access_token: Optional[str] = None

class AzureDevOpsConfigInDB(AzureDevOpsConfigBase):
    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class AzureDevOpsConfigResponse(AzureDevOpsConfigInDB):
    pass

class DevOpsProjectBase(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None

class DevOpsProjectCreate(DevOpsProjectBase):
    organization_id: int

class DevOpsProjectInDB(DevOpsProjectBase):
    id: int
    organization_id: int

    class Config:
        orm_mode = True

class DevOpsProjectResponse(DevOpsProjectInDB):
    pass

class DevOpsTeamBase(BaseModel):
    team_id: str
    name: str

class DevOpsTeamCreate(DevOpsTeamBase):
    project_id: int

class DevOpsTeamInDB(DevOpsTeamBase):
    id: int
    project_id: int

    class Config:
        orm_mode = True

class DevOpsTeamResponse(DevOpsTeamInDB):
    pass

class WorkItemTypeBase(BaseModel):
    name: str
    fields: Dict[str, Any]

class WorkItemTypeCreate(WorkItemTypeBase):
    project_id: int

class WorkItemTypeInDB(WorkItemTypeBase):
    id: int
    project_id: int

    class Config:
        orm_mode = True

class WorkItemTypeResponse(WorkItemTypeInDB):
    pass

class DevOpsCacheBase(BaseModel):
    cache_key: str
    cache_value: Dict[str, Any]
    expires_at: datetime

class DevOpsCacheCreate(DevOpsCacheBase):
    organization_id: int

class DevOpsCacheInDB(DevOpsCacheBase):
    id: int
    organization_id: int

    class Config:
        orm_mode = True

class DevOpsCacheResponse(DevOpsCacheInDB):
    pass

# Project Management Query schema
class ProjectManagementQuery(BaseModel):
    query: str
    project: str
    team: str

# Response schemas for API endpoints
class ProjectResponse(BaseModel):
    id: str
    name: str

class TeamResponse(BaseModel):
    id: str
    name: str