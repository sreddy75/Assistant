from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict, Union
from fastapi import UploadFile, File

class OrganizationBase(BaseModel):
    name: Optional[str] = None
    roles: Optional[List[str]] = Field(default_factory=list)
    assistants: Optional[Dict] = Field(default_factory=dict)
    feature_flags: Optional[Dict] = Field(default_factory=dict)

class OrganizationCreate(OrganizationBase):
    name: str

class OrganizationUpdate(OrganizationBase):
    pass

class OrganizationInDB(OrganizationBase):
    id: int
    config_id: int

    class Config:
        orm_mode = True

class OrganizationWithFiles(OrganizationBase):
    instructions: Optional[UploadFile] = File(None)
    chat_system_icon: Optional[UploadFile] = File(None)
    chat_user_icon: Optional[UploadFile] = File(None)
    config_toml: Optional[UploadFile] = File(None)
    main_image: Optional[UploadFile] = File(None)
    azure_devops_config: Optional[str] = None

class OrganizationResponse(BaseModel):
    id: int
    name: str
    roles: Dict[str, Any]
    assistants: Dict[str, Any] 
    feature_flags: Dict[str, bool]
    config_id: int
    instructions_path: Optional[str]
    chat_system_icon_path: Optional[str]
    chat_user_icon_path: Optional[str]
    config_toml: Optional[str]
    main_image_path: Optional[str]
    azure_devops_url: Optional[str]
    azure_devops_integrated: bool = Field(default=False)
    azure_devops_org_url: Optional[str]

    class Config:
        from_attributes = True    
class ThemeConfig(BaseModel):
    primaryColor: str
    backgroundColor: str
    secondaryBackgroundColor: str
    textColor: str
    font: str

class ConfigResponse(BaseModel):
    theme: ThemeConfig    