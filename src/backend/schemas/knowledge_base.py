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
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None

class DocumentSearch(BaseModel):
    query: str