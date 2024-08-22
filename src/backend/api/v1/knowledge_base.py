import base64
import io
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from src.backend.db.session import get_db
from src.backend.models.models import User
from src.backend.schemas.knowledge_base import DocumentCreate, DocumentResponse, DocumentUpdate, DocumentSearch
from src.backend.services.knowledge_base_service import KnowledgeBaseService
from src.backend.helpers.auth import get_current_user

router = APIRouter()

@router.post("/add-url", response_model=Dict[str, Any])
async def add_url(
    url: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    kb_service = KnowledgeBaseService(db, current_user)
    try:
        result = await kb_service.add_url(url)
        return {"success": True, "message": "URL added successfully", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/clear-knowledge-base", response_model=Dict[str, bool])
async def clear_knowledge_base(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    kb_service = KnowledgeBaseService(db, current_user)
    result = kb_service.clear_knowledge_base()
    return {"success": result}

@router.post("/upload-file", response_model=DocumentResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    content = await file.read()
    kb_service = KnowledgeBaseService(db, current_user)
    try:
        return await kb_service.process_file(file.filename, io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/search", response_model=List[DocumentResponse])
async def search_documents(
    search: DocumentSearch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    kb_service = KnowledgeBaseService(db, current_user)
    try:
        return kb_service.search_documents(search)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    kb_service = KnowledgeBaseService(db, current_user)
    try:
        return kb_service.get_documents()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/documents/{document_name}", response_model=DocumentResponse)
async def delete_document(
    document_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    kb_service = KnowledgeBaseService(db, current_user)
    try:
        return kb_service.delete_document(document_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/documents/{document_name}", response_model=DocumentResponse)
async def update_document(
    document_name: str,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    kb_service = KnowledgeBaseService(db, current_user)
    try:
        return kb_service.update_document(document_name, document_update)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))