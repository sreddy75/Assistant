from collections import defaultdict
import json
import re
from typing import Optional, List, Union, Dict, Any
from hashlib import md5
from datetime import datetime
import uuid
from sqlalchemy import Integer, delete, update, Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import create_engine, Engine
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import MetaData, Table
from sqlalchemy.sql.expression import text, func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from pgvector.sqlalchemy import Vector

from src.backend.kr8.document import Document
from src.backend.kr8.document.base import Usage
from src.backend.kr8.embedder import Embedder
from src.backend.kr8.embedder.openai import OpenAIEmbedder
from src.backend.kr8.vectordb.base import VectorDb
from src.backend.kr8.vectordb.distance import Distance
from src.backend.kr8.vectordb.pgvector.index import Ivfflat, HNSW
from src.backend.kr8.utils.log import logger

class PgVector2(VectorDb):
    def __init__(
        self,
        collection: str,
        schema: Optional[str] = "ai",
        db_url: Optional[str] = None,
        db_engine: Optional[Engine] = None,
        embedder: Optional[Embedder] = None,
        distance: Distance = Distance.cosine,
        index: Optional[Union[Ivfflat, HNSW]] = HNSW(),
        user_id: Optional[int] = None,
        org_id: Optional[int] = None,
        project_namespace: Optional[str] = None,
        async_session: Optional[async_sessionmaker[AsyncSession]] = None,
        custom_table: Optional[Table] = None
    ):
        self.project_namespace = project_namespace
        self.user_id = user_id
        self.org_id = org_id
        self.logger = logger
        self.collection = self.get_collection_name(collection)
        self.schema = schema
        self.db_url = db_url
        self.db_engine = db_engine or (create_engine(db_url) if db_url else None)
        self.metadata = MetaData(schema=self.schema)
        self.embedder = embedder or OpenAIEmbedder()
        self.dimensions = self.embedder.dimensions
        self.distance = distance
        self.index = index
        self.custom_table = custom_table
        self.table = self.get_table()

        if self.db_engine:
            self.Session = sessionmaker(bind=self.db_engine)
        else:
            self.Session = None

        if async_session:
            self.async_session = async_session
        elif db_url:
            async_engine = create_async_engine(db_url)
            self.async_session = async_sessionmaker(async_engine, expire_on_commit=False)
        else:
            self.async_session = None

    def get_collection_name(self, base_collection: str) -> str:
        parts = []
        if self.org_id:
            parts.append(f"org_{self.org_id}")
        if self.user_id:
            parts.append(f"user_{self.user_id}")
        parts.append(base_collection)
        if self.project_namespace:
            parts.append(self.project_namespace)
        return "_".join(parts)

    def get_table(self) -> Table:
        if self.custom_table is not None:  # Change this line
            required_columns = {
                'id': String,
                'embedding': Vector(self.dimensions),
                'created_at': DateTime(timezone=True),
                'updated_at': DateTime(timezone=True),
            }
            for col_name, col_type in required_columns.items():
                if col_name not in self.custom_table.c:
                    self.custom_table.append_column(Column(col_name, col_type))
            return self.custom_table
        else:
            return Table(
                self.collection,
                self.metadata,
                Column("id", String, primary_key=True),
                Column("name", String),
                Column("meta_data", postgresql.JSONB, server_default=text("'{}'::jsonb")),
                Column("content", String),
                Column("embedding", Vector(self.dimensions)),
                Column("usage", postgresql.JSONB),
                Column("created_at", DateTime(timezone=True), server_default=text("now()")),
                Column("updated_at", DateTime(timezone=True), onupdate=text("now()")),
                Column("content_hash", String),
                Column("user_id", Integer),
                Column("org_id", Integer),
                extend_existing=True,
            )

    def table_exists(self) -> bool:
        self.logger.debug(f"Checking if table exists: {self.table.name}")
        try:
            return inspect(self.db_engine).has_table(self.table.name, schema=self.schema)
        except Exception as e:
            self.logger.error(e)
            return False
        
    def ensure_table_exists(self):
        if not self.table_exists():
            self.create()

     
    def create(self) -> None:
        if not self.table_exists():
            with self.Session() as sess:
                with sess.begin():
                    try:
                        sess.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                        if self.schema:
                            sess.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema};"))
                        self.table.create(self.db_engine)
                        self.logger.info(f"Successfully created table: {self.collection}")
                    except Exception as e:
                        self.logger.error(f"Error creating table: {e}")
                        raise

    def upsert(self, documents: List[Document], batch_size: int = 20) -> None:
        self.ensure_table_exists() 
        with self.Session() as sess:
            counter = 0
            for document in documents:
                try:
                    document.embed(embedder=self.embedder)
                    cleaned_content = document.content.replace("\x00", "\ufffd")
                    content_hash = md5(cleaned_content.encode()).hexdigest()
                    _id = document.id or content_hash

                    # Ensure meta_data is a dictionary
                    meta_data = document.meta_data if isinstance(document.meta_data, dict) else {}

                    # For Confluence pages, add space_key and url to meta_data if they exist
                    if meta_data.get("type") == "confluence_page":
                        meta_data["space_key"] = meta_data.get("space_key")
                        meta_data["url"] = meta_data.get("url")

                    values = {
                        "id": _id,
                        "name": document.name,
                        "meta_data": meta_data,
                        "content": cleaned_content,
                        "embedding": document.embedding,
                        "usage": document.usage,
                        "content_hash": content_hash,
                        "user_id": self.user_id,
                        "org_id": self.org_id,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }

                    stmt = postgresql.insert(self.table).values(**values)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["id"],
                        set_={
                            col.name: stmt.excluded[col.name] 
                            for col in self.table.columns 
                            if col.name not in ['id', 'created_at']
                        }
                    )
                    sess.execute(stmt)
                    counter += 1

                    if counter >= batch_size:
                        sess.commit()
                        self.logger.info(f"Committed {counter} documents")
                        counter = 0
                except Exception as e:
                    self.logger.error(f"Error upserting document: {e}")
                    self.logger.exception("Traceback:")
                    sess.rollback()

            if counter > 0:
                sess.commit()
                self.logger.info(f"Committed final {counter} documents")

    def search(self, query: str, limit: int = 5, collection: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            self.logger.error(f"Error getting embedding for Query: {query}")
            return []

        columns = [col for col in self.table.columns if col.name != 'embedding']
        columns.append(self.table.c.embedding)

        stmt = select(*columns)

        if filters:
            for key, value in filters.items():
                if hasattr(self.table.c, key):
                    stmt = stmt.where(getattr(self.table.c, key) == value)
                else:
                    # For metadata fields, including Confluence-specific ones
                    stmt = stmt.where(self.table.c.meta_data[key].astext == str(value))

        if self.user_id and hasattr(self.table.c, 'user_id'):
            stmt = stmt.where(self.table.c.user_id == self.user_id)

        if self.distance == Distance.l2:
            stmt = stmt.order_by(self.table.c.embedding.l2_distance(query_embedding))
        elif self.distance == Distance.cosine:
            stmt = stmt.order_by(self.table.c.embedding.cosine_distance(query_embedding))
        elif self.distance == Distance.max_inner_product:
            stmt = stmt.order_by(self.table.c.embedding.max_inner_product(query_embedding))

        stmt = stmt.limit(limit=limit)

        try:
            with self.Session() as sess:
                with sess.begin():
                    if self.index:
                        if isinstance(self.index, Ivfflat):
                            sess.execute(text(f"SET LOCAL ivfflat.probes = {self.index.probes}"))
                        elif isinstance(self.index, HNSW):
                            sess.execute(text(f"SET LOCAL hnsw.ef_search  = {self.index.ef_search}"))
                    neighbors = sess.execute(stmt).fetchall() or []
        except Exception as e:
            self.logger.error(f"Error searching for documents: {e}")
            return []

        search_results = []
        for neighbor in neighbors:
            doc_dict = {col.name: getattr(neighbor, col.name) for col in self.table.columns if col.name != 'embedding'}
            doc_dict['embedding'] = neighbor.embedding
            doc = Document(**doc_dict)
            search_results.append(doc)

        return search_results
    
    def get_document_by_name(self, name: str) -> Optional[Document]:
        with self.Session() as sess:
            with sess.begin():
                stmt = select(self.table).where(self.table.c.name == name)
                if self.user_id and hasattr(self.table.c, 'user_id'):
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                result = sess.execute(stmt).first()
                if result:
                    doc_dict = {col.name: getattr(result, col.name) for col in self.table.columns if col.name != 'embedding'}
                    doc_dict['embedding'] = result.embedding
                    return Document(**doc_dict)
        return None

    def get_all_documents(self) -> List[Document]:
        with self.Session() as sess:
            with sess.begin():
                stmt = select(self.table)
                if self.user_id and hasattr(self.table.c, 'user_id'):
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                results = sess.execute(stmt).fetchall()
                return [Document(**{col.name: getattr(result, col.name) for col in self.table.columns}) for result in results]

    def delete_document(self, identifier: str) -> bool:
        with self.Session() as sess:
            with sess.begin():
                base_name = re.sub(r'_chunk_\d+$', '', identifier)
                pattern = f"{base_name}%"
                stmt = delete(self.table).where(self.table.c.name.like(pattern))
                if self.user_id and hasattr(self.table.c, 'user_id'):
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                result = sess.execute(stmt)
                deleted_count = result.rowcount
                if deleted_count > 0:
                    self.logger.info(f"Deleted {deleted_count} chunks for document: {identifier}")
                    return True
                else:
                    self.logger.warning(f"No chunks found for document: {identifier}")
                    return False

    def update_document(self, document: Document) -> None:
        with self.Session() as sess:
            values = {col.name: getattr(document, col.name, None) for col in self.table.columns if col.name != 'id'}
            stmt = update(self.table).where(self.table.c.id == document.id).values(**values)
            sess.execute(stmt)
            sess.commit()

    def clear(self) -> bool:
        with self.Session() as sess:
            with sess.begin():
                stmt = delete(self.table)
                if self.user_id and hasattr(self.table.c, 'user_id'):
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                sess.execute(stmt)
                return True

    def optimize(self) -> None:
        if not self.index:
            return

        index_distance = "vector_cosine_ops"
        if self.distance == Distance.l2:
            index_distance = "vector_l2_ops"
        elif self.distance == Distance.max_inner_product:
            index_distance = "vector_ip_ops"

        with self.Session() as sess:
            with sess.begin():
                if isinstance(self.index, Ivfflat):
                    sess.execute(text(f"SET ivfflat.probes = {self.index.probes}"))
                    sess.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {self.index.name} ON {self.table.name} "
                        f"USING ivfflat (embedding {index_distance}) WITH (lists = {self.index.lists})"
                    ))
                elif isinstance(self.index, HNSW):
                    sess.execute(text(f"SET hnsw.ef_search = {self.index.ef_search}"))
                    sess.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {self.index.name} ON {self.table.name} "
                        f"USING hnsw (embedding {index_distance}) "
                        f"WITH (m = {self.index.m}, ef_construction = {self.index.ef_construction})"
                    ))

        self.logger.info("Optimized vector database")

    def count_documents(self) -> int:
        try:
            with self.Session() as sess:
                with sess.begin():
                    count = sess.query(func.count(self.table.c.id)).scalar()
                    self.logger.info(f"Found {count} documents.")
                    return count
        except Exception as e:
            self.logger.error(f"Error counting documents: {str(e)}")
            return 0

    def list_document_names(self) -> List[Dict[str, Any]]:
        with self.Session() as sess:
            with sess.begin():
                stmt = select(self.table.c.name)
                if self.user_id and hasattr(self.table.c, 'user_id'):
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                if self.org_id and hasattr(self.table.c, 'org_id'):
                    stmt = stmt.where(self.table.c.org_id == self.org_id)
                
                results = sess.execute(stmt).fetchall()
                
                grouped_docs = defaultdict(int)
                for (name,) in results:
                    base_name = re.sub(r'_chunk_\d+$', '', name)
                    grouped_docs[base_name] += 1
                
                document_info = [
                    {"name": name, "chunks": count}
                    for name, count in grouped_docs.items()
                ]
                
                self.logger.debug(f"Document info: {document_info}")
                
                return document_info

    def get_document_content(self, document_name: str) -> str:
        with self.Session() as sess:
            stmt = select(self.table.c.content).where(self.table.c.name == document_name)
            if self.user_id and hasattr(self.table.c, 'user_id'):
                stmt = stmt.where(self.table.c.user_id == self.user_id)
            result = sess.execute(stmt).first()
            return result[0] if result else ""
        
    async def upsert_async(self, documents: List[Document], batch_size: int = 20) -> None:
        if not self.async_session:
            raise ValueError("Async session not available.")

        async with self.async_session() as sess:
            async with sess.begin():
                for i, document in enumerate(documents):
                    try:
                        document.embed(embedder=self.embedder)
                        cleaned_content = document.content.replace("\x00", "\ufffd")
                        content_hash = md5(cleaned_content.encode()).hexdigest()
                        _id = document.id or content_hash

                        values = {
                            "id": _id,
                            "name": document.name,
                            "meta_data": document.meta_data,
                            "content": cleaned_content,
                            "embedding": document.embedding,
                            "usage": document.usage,
                            "content_hash": content_hash,
                            "user_id": self.user_id,
                            "org_id": self.org_id,
                        }

                        stmt = postgresql.insert(self.table).values(**values)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=["id"],
                            set_={col.name: stmt.excluded[col.name] for col in self.table.columns if col.name != 'id'}
                        )
                        await sess.execute(stmt)

                        if (i + 1) % batch_size == 0:
                            await sess.commit()
                            self.logger.info(f"Committed {batch_size} documents")

                    except Exception as e:
                        self.logger.error(f"Error upserting document asynchronously: {e}")
                        self.logger.exception("Traceback:")

                if (i + 1) % batch_size != 0:
                    await sess.commit()
                    self.logger.info(f"Committed final {(i + 1) % batch_size} documents")
    
    def doc_exists(self, document: Document) -> bool:
        with self.Session() as sess:
            with sess.begin():
                cleaned_content = document.content.replace("\x00", "\ufffd")
                stmt = select(self.table.c.content_hash).where(
                    self.table.c.content_hash == md5(cleaned_content.encode()).hexdigest()
                )
                result = sess.execute(stmt).first()
                return result is not None

    def name_exists(self, name: str) -> bool:
        with self.Session() as sess:
            with sess.begin():
                stmt = select(self.table.c.name).where(self.table.c.name == name)
                result = sess.execute(stmt).first()
                return result is not None

    def id_exists(self, id: str) -> bool:
        with self.Session() as sess:
            with sess.begin():
                stmt = select(self.table.c.id).where(self.table.c.id == id)
                result = sess.execute(stmt).first()
                return result is not None

    def insert(self, documents: List[Document], batch_size: int = 10) -> None:
        with self.Session() as sess:
            counter = 0
            for document in documents:
                document.embed(embedder=self.embedder)
                cleaned_content = document.content.replace("\x00", "\ufffd")
                content_hash = md5(cleaned_content.encode()).hexdigest()
                
                values = {
                    "id": document.id,
                    "name": document.name,
                    "meta_data": document.meta_data,
                    "content": cleaned_content,
                    "embedding": document.embedding,
                    "usage": Usage.from_dict(document.usage).to_dict(),
                    "content_hash": content_hash,
                    "user_id": self.user_id,
                    "org_id": self.org_id,
                }
                
                stmt = self.table.insert().values(**values)
                sess.execute(stmt)
                counter += 1

                if counter >= batch_size:
                    sess.commit()
                    self.logger.info(f"Committed {counter} documents")
                    counter = 0

            if counter > 0:
                sess.commit()
                self.logger.info(f"Committed final {counter} documents")

    def upsert_available(self) -> bool:
        return True

    def delete(self, collection: Optional[str] = None) -> None:
        collection = collection or self.collection
        if self.table_exists():
            with self.Session() as sess:
                with sess.begin():
                    sess.execute(text(f"DROP TABLE IF EXISTS {collection}"))
            self.logger.info(f"Deleted collection: {collection}")

    def exists(self) -> bool:
        return self.table_exists()

    def update_document_content(self, id: str, new_content: str) -> Optional[Document]:
        document = self.get_document_by_id(id)
        if document:
            document.content = new_content
            document.embed(embedder=self.embedder)
            self.update_document(document)
            return document
        return None

    def delete_document_by_name(self, name: str) -> bool:
        with self.Session() as sess:
            with sess.begin():
                stmt = delete(self.table).where(self.table.c.name == name)
                if self.user_id and hasattr(self.table.c, 'user_id'):
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                result = sess.execute(stmt)
                deleted = result.rowcount > 0
                if deleted:
                    self.logger.info(f"Deleted document: {name}")
                else:
                    self.logger.warning(f"No document found with name: {name}")
                return deleted

    def get_document_by_id(self, id: str) -> Optional[Document]:
        with self.Session() as sess:
            with sess.begin():
                stmt = select(self.table).where(self.table.c.id == id)
                if self.user_id and hasattr(self.table.c, 'user_id'):
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                result = sess.execute(stmt).first()
                if result:
                    doc_dict = {col.name: getattr(result, col.name) for col in self.table.columns if col.name != 'embedding'}
                    doc_dict['embedding'] = result.embedding
                    return Document(**doc_dict)
        return None

    def update_document_usage(self, documents: List[Document]):
        with self.Session() as sess:
            for doc in documents:
                if hasattr(self.table.c, 'usage'):
                    stmt = (
                        update(self.table)
                        .where(self.table.c.id == doc.id)
                        .values(usage=doc.usage)
                    )
                    sess.execute(stmt)
            sess.commit()

    async def insert_async(self, documents: List[Document], batch_size: int = 10) -> None:
        if not self.async_session:
            raise ValueError("Async session not available.")

        async with self.async_session() as sess:
            async with sess.begin():
                counter = 0
                for document in documents:
                    document.embed(embedder=self.embedder)
                    cleaned_content = document.content.replace("\x00", "\ufffd")
                    content_hash = md5(cleaned_content.encode()).hexdigest()
                    
                    values = {
                        "id": document.id,
                        "name": document.name,
                        "meta_data": document.meta_data,
                        "content": cleaned_content,
                        "embedding": document.embedding,
                        "usage": Usage.from_dict(document.usage).to_dict(),
                        "content_hash": content_hash,
                        "user_id": self.user_id,
                        "org_id": self.org_id,
                    }
                    
                    stmt = self.table.insert().values(**values)
                    await sess.execute(stmt)
                    counter += 1

                    if counter >= batch_size:
                        await sess.commit()
                        self.logger.info(f"Committed {counter} documents")
                        counter = 0

                if counter > 0:
                    await sess.commit()
                    self.logger.info(f"Committed final {counter} documents")                        