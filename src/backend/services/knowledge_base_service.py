from src.kr8.vectordb.pgvector import PgVector2
from src.kr8.embedder.sentence_transformer import SentenceTransformerEmbedder
from src.kr8.document import Document as Kr8Document
from src.backend.models.models import User
from src.backend.schemas.knowledge_base import DocumentCreate, DocumentResponse, DocumentUpdate, DocumentSearch
from sqlalchemy.orm import Session
from typing import List
import os

class KnowledgeBaseService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.vector_db = PgVector2(
            collection="documents",
            db_url=os.getenv("DB_URL"),
            embedder=SentenceTransformerEmbedder(),
            user_id=user.id
        )

    def add_document(self, document: DocumentCreate) -> DocumentResponse:
        # Create a Kr8Document
        kr8_doc = Kr8Document(
            name=document.name,
            content=document.content,
            meta_data={**document.meta_data, "user_id": self.user.id} if document.meta_data else {"user_id": self.user.id}
        )
        
        # Add to vector database
        self.vector_db.insert([kr8_doc])
        
        # Create a response
        return DocumentResponse(
            id=kr8_doc.id,
            name=kr8_doc.name,
            content=kr8_doc.content,
            meta_data=kr8_doc.meta_data,
            user_id=self.user.id,
            created_at=kr8_doc.usage.get('created_at'),
            updated_at=kr8_doc.usage.get('updated_at')
        )

    def get_documents(self) -> List[DocumentResponse]:
        # This method needs to be implemented in PgVector2
        documents = self.vector_db.get_all_documents()
        return [
            DocumentResponse(
                id=doc.id,
                name=doc.name,
                content=doc.content,
                meta_data=doc.meta_data,
                user_id=self.user.id,
                created_at=doc.usage.get('created_at'),
                updated_at=doc.usage.get('updated_at')
            ) for doc in documents if doc.meta_data.get('user_id') == self.user.id
        ]

    def search_documents(self, search: DocumentSearch) -> List[DocumentResponse]:
        results = self.vector_db.search(search.query, limit=5)
        return [
            DocumentResponse(
                id=doc.id,
                name=doc.name,
                content=doc.content,
                meta_data=doc.meta_data,
                user_id=self.user.id,
                created_at=doc.usage.get('created_at'),
                updated_at=doc.usage.get('updated_at')
            ) for doc in results if doc.meta_data.get('user_id') == self.user.id
        ]

    def delete_document(self, document_name: str) -> DocumentResponse:
        document = self.vector_db.get_document_by_name(document_name)
        if not document or document.meta_data.get('user_id') != self.user.id:
            raise ValueError("Document not found")
        
        self.vector_db.delete_document_by_name(document_name)
        
        return DocumentResponse(
            id=document.id,
            name=document.name,
            content=document.content,
            meta_data=document.meta_data,
            user_id=self.user.id,
            created_at=document.usage.get('created_at'),
            updated_at=document.usage.get('updated_at')
        )

    def update_document(self, document_name: str, document_update: DocumentUpdate) -> DocumentResponse:
        document = self.vector_db.get_document_by_name(document_name)
        if not document or document.meta_data.get('user_id') != self.user.id:
            raise ValueError("Document not found")

        update_data = document_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(document, key, value)

        self.vector_db.upsert([document])

        return DocumentResponse(
            id=document.id,
            name=document.name,
            content=document.content,
            meta_data=document.meta_data,
            user_id=self.user.id,
            created_at=document.usage.get('created_at'),
            updated_at=document.usage.get('updated_at')
        )