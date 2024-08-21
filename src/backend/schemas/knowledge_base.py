from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class DocumentBase(BaseModel):
    name: str
    content: str
    meta_data: Optional[Dict[str, Any]] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: str
    name: str
    content: str
    meta_data: Dict[str, Any]
    user_id: int
    org_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    chunks: int = 1

    class Config:
        orm_mode = True

class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None

class DocumentSearch(BaseModel):
    query: str