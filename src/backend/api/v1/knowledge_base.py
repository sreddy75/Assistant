from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.backend.db.session import get_db
from src.backend.models.models import User
from src.backend.schemas.knowledge_base import DocumentCreate, DocumentResponse, DocumentUpdate, DocumentSearch
from src.backend.services.knowledge_base_service import KnowledgeBaseService
from src.backend.helpers.auth import get_current_user

router = APIRouter()

router = APIRouter()

@router.post("/documents", response_model=DocumentResponse)
async def add_document(
    document: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    kb_service = KnowledgeBaseService(db, current_user)
    return kb_service.add_document(document)

@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    kb_service = KnowledgeBaseService(db, current_user)
    return kb_service.get_documents()

@router.post("/search", response_model=List[DocumentResponse])
async def search_documents(
    search: DocumentSearch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    kb_service = KnowledgeBaseService(db, current_user)
    return kb_service.search_documents(search)

@router.delete("/documents/{document_name}", response_model=DocumentResponse)
async def delete_document(
    document_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    kb_service = KnowledgeBaseService(db, current_user)
    return kb_service.delete_document(document_name)

@router.put("/documents/{document_name}", response_model=DocumentResponse)
async def update_document(
    document_name: str,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    kb_service = KnowledgeBaseService(db, current_user)
    return kb_service.update_document(document_name, document_update)