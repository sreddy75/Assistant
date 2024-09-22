import json
from typing import List, Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, Table, Column, Integer, String, Text, MetaData, text
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector
from src.backend.kr8.document.base import Document
from src.backend.kr8.vectordb.pgvector.pgvector2 import PgVector2

class AzureDevOpsKnowledge:
    def __init__(self, db_url: str, embedder, org_id: int, user_id: Optional[int] = None):
        self.metadata = MetaData()
        self.org_id = org_id
        self.user_id = user_id
        self.custom_table = self.get_custom_table()
        self.vector_db = PgVector2(
            collection="azure_devops_endpoints",
            db_url=db_url,
            embedder=embedder,
            org_id=org_id,
            user_id=user_id,
            custom_table=self.custom_table
        )

    def get_custom_table(self):
        return Table(
            'azure_devops_endpoints',
            self.metadata,
            Column('id', String, primary_key=True),
            Column('org_id', Integer, ForeignKey("organizations.id"), nullable=False, index=True),
            Column('user_id', Integer, ForeignKey("users.id"), nullable=True, index=True),
            Column('name', String, nullable=False),
            Column('path', String, nullable=False),
            Column('method', String, nullable=False),
            Column('description', Text, nullable=True),
            Column('parameters', postgresql.JSONB, nullable=True),
            Column('response_schema', postgresql.JSONB, nullable=True),
            Column('meta_data', postgresql.JSONB, nullable=True),
            Column('content', Text, nullable=True),
            Column('embedding', Vector(384), nullable=True),
            Column('usage', postgresql.JSONB, nullable=True),
            Column('content_hash', String, nullable=True),
            Column('created_at', DateTime(timezone=True), server_default=text("now()")),
            Column('updated_at', DateTime(timezone=True), onupdate=text("now()")),
            extend_existing=True
        )

    def fetch_and_store_endpoints(self, swagger_json):
        documents = []
        paths = swagger_json.get('paths', {})
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                doc_id = str(uuid.uuid4())
                name = f"{method.upper()} {path}"
                description = operation.get('description', '')
                parameters = operation.get('parameters', [])
                response_schema = operation.get('responses', {})
                content = json.dumps({
                    "path": path,
                    "method": method.upper(),
                    "description": description,
                    "parameters": parameters,
                    "response_schema": response_schema
                })
                meta_data = {
                    "type": "azure_devops_endpoint",
                    "path": path,
                    "method": method.upper(),
                    "description": description,
                    "org_id": self.org_id,
                    "user_id": self.user_id
                }

                doc = Document(
                    id=doc_id,
                    name=name,
                    content=content,
                    meta_data=meta_data
                )
                documents.append(doc)

        self.vector_db.upsert(documents)

    def search_endpoints(self, query: str, limit: int = 5) -> List[Document]:
        return self.vector_db.search(query=query, limit=limit)

    def get_all_endpoints(self) -> List[Document]:
        return self.vector_db.get_all_documents()

    def get_endpoint_by_name(self, name: str) -> Optional[Document]:
        return self.vector_db.get_document_by_name(name)

    def delete_endpoint(self, name: str) -> bool:
        return self.vector_db.delete_document_by_name(name)

    def clear_all_endpoints(self) -> bool:
        return self.vector_db.clear()