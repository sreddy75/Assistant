from pydantic import BaseModel, Field
from typing import Optional, List, Dict
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

class OrganizationResponse(OrganizationInDB):
    instructions_path: Optional[str] = None
    chat_system_icon_path: Optional[str] = None
    chat_user_icon_path: Optional[str] = None
    config_toml_path: Optional[str] = None
    main_image_path: Optional[str] = None