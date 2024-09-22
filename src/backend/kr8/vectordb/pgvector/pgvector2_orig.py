from collections import defaultdict
import re
from typing import Optional, List, Union, Dict, Any
from hashlib import md5
from datetime import datetime
import uuid
from sqlalchemy import Integer, delete, update
from ...document.base import Usage
from src.backend.kr8.embedder.openai import OpenAIEmbedder
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError

try:
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.engine import create_engine, Engine
    from sqlalchemy.inspection import inspect
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.schema import MetaData, Table, Column
    from sqlalchemy.sql.expression import text, func, select
    from sqlalchemy.types import DateTime, String
except ImportError:
    raise ImportError("`sqlalchemy` not installed")

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    raise ImportError("`pgvector` not installed")

from src.backend.kr8.document import Document
from src.backend.kr8.embedder import Embedder
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
        
        # Collection attributes
        self.collection = self.get_collection_name(collection)
                                
        
        _engine: Optional[Engine] = db_engine
        if _engine is None and db_url is not None:
            _engine = create_engine(db_url)

        if _engine is None:
            raise ValueError("Must provide either db_url or db_engine")
                                
        self.schema: Optional[str] = schema

        # Database attributes
        self.db_url: Optional[str] = db_url
        self.db_engine: Engine = _engine
        self.metadata: MetaData = MetaData(schema=self.schema)        


        # Create sync engine if not provided
        if self.db_engine is None and db_url is not None:
            self.db_engine = create_engine(db_url)

        # Sync session
        if self.db_engine:
            self.Session = sessionmaker(bind=self.db_engine)
        else:
            self.Session = None

        # Async session
        if async_session:
            self.async_session = async_session
        elif db_url:
            async_engine = create_async_engine(db_url)
            self.async_session = async_sessionmaker(async_engine, expire_on_commit=False)
        else:
            self.async_session = None
            
        # Embedder for embedding the document contents
        _embedder = embedder
        
        if _embedder is None:            
            _embedder = OpenAIEmbedder()
            
        self.embedder: Embedder = _embedder
        self.dimensions: int = self.embedder.dimensions

        # Distance metric
        self.distance: Distance = distance

        # Index for the collection
        self.index: Optional[Union[Ivfflat, HNSW]] = index

        # Database session
        if async_session:
            self.async_session = async_session
        else:
            self.Session = sessionmaker(bind=self.db_engine)
        
        self.custom_table = custom_table
        self.table = self.get_table()

    def get_table(self) -> Table:
        if self.custom_table:
            # Ensure the custom table has the required columns
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
            # Default table structure
            return Table(
                self.collection,
                self.metadata,
                Column("id", String, primary_key=True),
                Column("name", String),
                Column("meta_data", JSONB, server_default=text("'{}'::jsonb")),
                Column("content", String),
                Column("embedding", Vector(self.dimensions)),
                Column("usage", JSONB),
                Column("created_at", DateTime(timezone=True), server_default=text("now()")),
                Column("updated_at", DateTime(timezone=True), onupdate=text("now()")),
                Column("content_hash", String),
                Column("user_id", Integer),
                Column("org_id", Integer),
                extend_existing=True,
            )
    
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

    def table_exists(self) -> bool:
        logger.debug(f"Checking if table exists: {self.table.name}")
        try:
            return inspect(self.db_engine).has_table(self.table.name, schema=self.schema)
        except Exception as e:
            logger.error(e)
            return False

    def create(self) -> None:
        if not self.table_exists():
            with self.Session() as sess:
                with sess.begin():
                    try:
                        logger.debug("Creating extension: vector")
                        sess.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                        if self.schema is not None:
                            logger.debug(f"Creating schema: {self.schema}")
                            sess.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema};"))
                        logger.debug(f"Creating table: {self.collection}")
                        self.table.create(self.db_engine)
                        logger.info(f"Successfully created table: {self.collection}")
                    except Exception as e:
                        logger.error(f"Error creating table: {e}")
                        raise

    def doc_exists(self, document: Document) -> bool:
        """
        Validating if the document exists or not

        Args:
            document (Document): Document to validate
        """
        columns = [self.table.c.name, self.table.c.content_hash]
        with self.Session() as sess:
            with sess.begin():
                cleaned_content = document.content.replace("\x00", "\ufffd")
                stmt = select(*columns).where(self.table.c.content_hash == md5(cleaned_content.encode()).hexdigest())
                result = sess.execute(stmt).first()
                return result is not None

    def get_document_by_name(self, name: str) -> Optional[Document]:
        with self.Session() as sess:
            with sess.begin():
                stmt = select(self.table).where(self.table.c.name == name)
                if self.user_id:
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                result = sess.execute(stmt).first()
                if result:
                    usage_dict = Usage.from_dict(result.usage).to_dict() if result.usage else {}
                    self.logger.debug(f"Retrieved document: {name}")
                    self.logger.debug(f"Document metadata: {result.meta_data}")
                    self.logger.debug(f"Document usage: {usage_dict}")
                    return Document(
                        id=result.id,
                        name=result.name,
                        meta_data=result.meta_data,
                        content=result.content,
                        embedder=self.embedder,
                        embedding=result.embedding,
                        usage=usage_dict,
                    )
                else:
                    self.logger.warning(f"No document found with name: {name}")
        return None

    def get_all_documents(self) -> List[Document]:
        with self.Session() as sess:
            with sess.begin():
                stmt = select(self.table)
                if self.user_id:
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                results = sess.execute(stmt).fetchall()
                return [
                    Document(
                        id=result.id,
                        name=result.name,
                        meta_data=result.meta_data,
                        content=result.content,
                        embedder=self.embedder,
                        embedding=result.embedding,
                        usage=Usage.from_dict(result.usage).to_dict() if result.usage else {},
                    ) for result in results
                ]
                
    def name_exists(self, name: str) -> bool:
        """
        Validate if a row with this name exists or not

        Args:
            name (str): Name to check
        """
        with self.Session() as sess:
            with sess.begin():
                stmt = select(self.table.c.name).where(self.table.c.name == name)
                result = sess.execute(stmt).first()
                return result is not None

    def id_exists(self, id: str) -> bool:
        """
        Validate if a row with this id exists or not

        Args:
            id (str): Id to check
        """
        with self.Session() as sess:
            with sess.begin():
                stmt = select(self.table.c.id).where(self.table.c.id == id)
                result = sess.execute(stmt).first()
                return result is not None

    def insert(self, documents: List[Document], batch_size: int = 10) -> None:
        with self.Session() as sess:
            counter = 0
            for document in documents:
                logger.info(f"Embedding document: {document.name}")
                document.embed(embedder=self.embedder)
                logger.info(f"Embedded document: {document.name}, embedding shape: {len(document.embedding)}")
                cleaned_content = document.content.replace("\x00", "\ufffd")
                content_hash = md5(cleaned_content.encode()).hexdigest()                
                usage = Usage.from_dict(document.usage)
                logger.info(f"Inserting document into vector DB:")
                logger.info(f"  Name: {document.name}")
                logger.info(f"  Metadata: {document.meta_data}")
                logger.info(f"  Usage: {usage.to_dict()}")
                logger.info(f"  Content preview: {cleaned_content[:100]}...")
                stmt = postgresql.insert(self.table).values(
                    id=document.id,
                    name=document.name,
                    meta_data=document.meta_data,
                    content=cleaned_content,
                    embedding=document.embedding,
                    usage=usage.to_dict(),
                    content_hash=content_hash,
                    user_id=self.user_id,
                    org_id=self.org_id,
                )
                sess.execute(stmt)
                counter += 1
                logger.debug(f"Inserted document: {document.name} ({document.meta_data})")

                # Commit every `batch_size` documents
                if counter >= batch_size:
                    sess.commit()
                    logger.info(f"Committed {counter} documents")
                    counter = 0

            # Commit any remaining documents
            if counter > 0:
                sess.commit()
                logger.info(f"Committed {counter} documents")

    def upsert_available(self) -> bool:
        return True

    def clear(self) -> bool:
        with self.Session() as sess:
            with sess.begin():
                stmt = delete(self.table)
                if self.user_id:
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                result = sess.execute(stmt)
                return result.rowcount > 0

    def delete(self, collection: Optional[str] = None) -> None:
        collection = collection or self.collection
        if self.table_exists():
            with self.Session() as sess:
                with sess.begin():
                    sess.execute(text(f"DROP TABLE IF EXISTS {collection}"))
            self.logger.info(f"Deleted collection: {collection}")

    def exists(self) -> bool:
        return self.table_exists()

    def optimize(self) -> None:
        if self.index is None:
            return

        with self.Session() as sess:
            with sess.begin():
                if isinstance(self.index, Ivfflat):
                    sess.execute(text(f"SET ivfflat.probes = {self.index.probes}"))
                    sess.execute(text(f"CREATE INDEX IF NOT EXISTS {self.index.name} ON {self.table.name} USING ivfflat (embedding vector_l2_ops) WITH (lists = {self.index.lists})"))
                elif isinstance(self.index, HNSW):
                    sess.execute(text(f"SET hnsw.ef_search = {self.index.ef_search}"))
                    sess.execute(text(f"CREATE INDEX IF NOT EXISTS {self.index.name} ON {self.table.name} USING hnsw (embedding vector_l2_ops) WITH (m = {self.index.m}, ef_construction = {self.index.ef_construction})"))
        
        self.logger.info("Optimized vector database")
        
    def upsert(self, documents: List[Document], batch_size: int = 20) -> None:
        with self.Session() as sess:
            counter = 0
            for document in documents:
                try:
                    document.embed(embedder=self.embedder)
                    cleaned_content = document.content.replace("\x00", "\ufffd")
                    content_hash = md5(cleaned_content.encode()).hexdigest()
                    _id = document.id or content_hash

                    # Prepare the values dict based on the table columns
                    values = {
                        "id": _id,
                        "embedding": document.embedding,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }

                    # Add other fields if they exist in the table
                    for field in ['name', 'meta_data', 'content', 'usage', 'content_hash', 'user_id', 'org_id']:
                        if hasattr(self.table.c, field):
                            values[field] = getattr(document, field, None)

                    # Add custom fields from document.meta_data if they exist in the table
                    for field, value in document.meta_data.items():
                        if hasattr(self.table.c, field):
                            values[field] = value

                    stmt = postgresql.insert(self.table).values(**values)
                    
                    # Update row when id matches
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["id"],
                        set_={col.name: stmt.excluded[col.name] for col in self.table.columns if col.name != 'id'}
                    )
                    sess.execute(stmt)
                    counter += 1

                    if counter >= batch_size:
                        sess.commit()
                        logger.info(f"Committed {counter} documents")
                        counter = 0
                except Exception as e:
                    logger.error(f"Error upserting document: {e}")
                    logger.exception("Traceback:")
                    sess.rollback()

            if counter > 0:
                sess.commit()
                logger.info(f"Committed final {counter} documents")

    async def upsert_async(self, documents: List[Document], batch_size: int = 20) -> None:
        if not self.async_session:
            raise ValueError("Async session not available. Make sure to provide db_url or async_session in the constructor.")

        logger.debug(f"Upserting {len(documents)} documents asynchronously")
        try:
            async with self.async_session() as sess:
                async with sess.begin():
                    counter = 0
                    for document in documents:
                        try:
                            logger.debug(f"Processing document: {document.name}")
                            document.embed(embedder=self.embedder)
                            cleaned_content = document.content.replace("\x00", "\ufffd")
                            content_hash = md5(cleaned_content.encode()).hexdigest()
                            _id = document.id or content_hash
                            logger.debug(f"Upserting document into vector DB: {_id}")
                            stmt = postgresql.insert(self.table).values(
                                id=_id,
                                name=document.name,
                                meta_data=document.meta_data,
                                content=cleaned_content,
                                embedding=document.embedding,
                                usage=document.usage,
                                content_hash=content_hash,
                                user_id=self.user_id,
                                org_id=self.org_id,
                            )
                            stmt = stmt.on_conflict_do_update(
                                index_elements=["id"],
                                set_=dict(
                                    name=stmt.excluded.name,
                                    meta_data=stmt.excluded.meta_data,
                                    content=stmt.excluded.content,
                                    embedding=stmt.excluded.embedding,
                                    usage=stmt.excluded.usage,
                                    content_hash=stmt.excluded.content_hash,
                                ),
                            )
                            await sess.execute(stmt)
                            counter += 1
                            logger.debug(f"Upserted document: {document.id} | {document.name} | {document.meta_data}")

                            if counter >= batch_size:
                                await sess.commit()
                                logger.info(f"Committed {counter} documents")
                                counter = 0
                        except Exception as e:
                            logger.error(f"Error upserting document {document.name}: {str(e)}")
                            logger.exception("Traceback:")

                    if counter > 0:
                        await sess.commit()
                        logger.info(f"Committed final {counter} documents")
        except ImportError as e:
            if "greenlet" in str(e):
                logger.error("The greenlet library is required for async operations. Please install it using 'pip install greenlet'.")
            raise
        except Exception as e:
            logger.error(f"Error in upsert_async: {str(e)}")
            logger.exception("Traceback:")
        finally:
            logger.debug("Finished upsert_async operation")

    async def insert_async(self, documents: List[Document], batch_size: int = 10) -> None:
        if not self.async_session:
            raise ValueError("Async session not available. Make sure to provide db_url or async_session in the constructor.")

        async with self.async_session() as sess:
            async with sess.begin():
                counter = 0
                for document in documents:
                    try:
                        logger.info(f"Embedding document: {document.name}")
                        document.embed(embedder=self.embedder)
                        logger.info(f"Embedded document: {document.name}, embedding shape: {len(document.embedding)}")
                        cleaned_content = document.content.replace("\x00", "\ufffd")
                        content_hash = md5(cleaned_content.encode()).hexdigest()                
                        usage = Usage.from_dict(document.usage)
                        logger.info(f"Inserting document into vector DB:")
                        logger.info(f"  Name: {document.name}")
                        logger.info(f"  Metadata: {document.meta_data}")
                        logger.info(f"  Usage: {usage.to_dict()}")
                        logger.info(f"  Content preview: {cleaned_content[:100]}...")
                        stmt = postgresql.insert(self.table).values(
                            id=document.id,
                            name=document.name,
                            meta_data=document.meta_data,
                            content=cleaned_content,
                            embedding=document.embedding,
                            usage=usage.to_dict(),
                            content_hash=content_hash,
                            user_id=self.user_id,
                            org_id=self.org_id,
                        )
                        await sess.execute(stmt)
                        counter += 1
                        logger.debug(f"Inserted document: {document.name} ({document.meta_data})")

                        if counter >= batch_size:
                            await sess.commit()
                            logger.info(f"Committed {counter} documents")
                            counter = 0
                    except Exception as e:
                        logger.error(f"Error inserting document: {e}")
                        logger.exception("Traceback:")

                if counter > 0:
                    await sess.commit()
                    logger.info(f"Committed final {counter} documents")
    def search(self, query: str, limit: int = 5, collection: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        columns = [col for col in self.table.columns if col.name != 'embedding']
        columns.append(self.table.c.embedding)

        stmt = select(*columns)

        if filters:
            for key, value in filters.items():
                if hasattr(self.table.c, key):
                    stmt = stmt.where(getattr(self.table.c, key) == value)

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
                    if self.index is not None:
                        if isinstance(self.index, Ivfflat):
                            sess.execute(text(f"SET LOCAL ivfflat.probes = {self.index.probes}"))
                        elif isinstance(self.index, HNSW):
                            sess.execute(text(f"SET LOCAL hnsw.ef_search  = {self.index.ef_search}"))
                    neighbors = sess.execute(stmt).fetchall() or []
        except Exception as e:
            logger.error(f"Error searching for documents: {e}")
            return []

        search_results = []
        for neighbor in neighbors:
            doc_dict = {col.name: getattr(neighbor, col.name) for col in self.table.columns if col.name != 'embedding'}
            doc_dict['embedding'] = neighbor.embedding
            doc = Document(**doc_dict)
            search_results.append(doc)

        return search_results

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
                if self.user_id:
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                result = sess.execute(stmt)
                deleted = result.rowcount > 0
                if deleted:
                    logger.info(f"Deleted document: {name}")
                else:
                    logger.warning(f"No document found with name: {name}")
                return deleted
            
    def delete_document(self, identifier: str) -> bool:
            with self.Session() as sess:
                with sess.begin():
                    # Create a pattern to match the document name and any potential chunks
                    base_name = re.sub(r'_chunk_\d+$', '', identifier)
                    pattern = f"{base_name}%"
                    
                    # Use the LIKE operator to match the document name and its chunks
                    stmt = delete(self.table).where(
                        self.table.c.name.like(pattern)
                    )
                    
                    if self.user_id:
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
            stmt = (
                update(self.table)
                .where(self.table.c.id == document.id)
                .values(
                    name=document.name,
                    meta_data=document.meta_data,
                    content=document.content,
                    embedding=document.embedding,
                    usage=document.usage,
                )
            )
            sess.execute(stmt)
            sess.commit()
    
    def get_document_by_id(self, id: str) -> Optional[Document]:
        with self.Session() as sess:
            with sess.begin():
                stmt = select(self.table).where(self.table.c.id == id)
                if self.user_id:
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                result = sess.execute(stmt).first()
                if result:
                    return Document(
                        id=result.id,
                        name=result.name,
                        meta_data=result.meta_data,
                        content=result.content,
                        embedder=self.embedder,
                        embedding=result.embedding,
                        usage=Usage.from_dict(result.usage),
                    )
        return None
                        
    def update_document_usage(self, documents: List[Document]):
        with self.Session() as sess:
            for doc in documents:
                stmt = (
                    update(self.table)
                    .where(self.table.c.name == doc.name)
                    .values(usage=doc.usage)
                )
                sess.execute(stmt)
            sess.commit()

    def delete(self) -> None:
        if self.table_exists():
            logger.debug(f"Deleting table: {self.collection}")
            self.table.drop(self.db_engine)

    def exists(self) -> bool:
        return self.table_exists()

    def get_count(self) -> int:
        with self.Session() as sess:
            with sess.begin():
                stmt = select(func.count(self.table.c.name)).select_from(self.table)
                result = sess.execute(stmt).scalar()
                if result is not None:
                    return int(result)
                return 0

    def optimize(self) -> None:
        from math import sqrt

        logger.debug("==== Optimizing Vector DB ====")
        if self.index is None:
            return

        if self.index.name is None:
            _type = "ivfflat" if isinstance(self.index, Ivfflat) else "hnsw"
            self.index.name = f"{self.collection}_{_type}_index"

        index_distance = "vector_cosine_ops"
        if self.distance == Distance.l2:
            index_distance = "vector_l2_ops"
        if self.distance == Distance.max_inner_product:
            index_distance = "vector_ip_ops"

        if isinstance(self.index, Ivfflat):
            num_lists = self.index.lists
            if self.index.dynamic_lists:
                total_records = self.get_count()
                logger.debug(f"Number of records: {total_records}")
                if total_records < 1000000:
                    num_lists = int(total_records / 1000)
                elif total_records > 1000000:
                    num_lists = int(sqrt(total_records))

            with self.Session() as sess:
                with sess.begin():
                    logger.debug(f"Setting configuration: {self.index.configuration}")
                    for key, value in self.index.configuration.items():
                        sess.execute(text(f"SET {key} = '{value}';"))
                    logger.debug(
                        f"Creating Ivfflat index with lists: {num_lists}, probes: {self.index.probes} "
                        f"and distance metric: {index_distance}"
                    )
                    sess.execute(text(f"SET ivfflat.probes = {self.index.probes};"))
                    sess.execute(
                        text(
                            f"CREATE INDEX IF NOT EXISTS {self.index.name} ON {self.table} "
                            f"USING ivfflat (embedding {index_distance}) "
                            f"WITH (lists = {num_lists});"
                        )
                    )
        elif isinstance(self.index, HNSW):
            with self.Session() as sess:
                with sess.begin():
                    logger.debug(f"Setting configuration: {self.index.configuration}")
                    for key, value in self.index.configuration.items():
                        sess.execute(text(f"SET {key} = '{value}';"))
                    logger.debug(
                        f"Creating HNSW index with m: {self.index.m}, ef_construction: {self.index.ef_construction} "
                        f"and distance metric: {index_distance}"
                    )
                    sess.execute(
                        text(
                            f"CREATE INDEX IF NOT EXISTS {self.index.name} ON {self.table} "
                            f"USING hnsw (embedding {index_distance}) "
                            f"WITH (m = {self.index.m}, ef_construction = {self.index.ef_construction});"
                        )
                    )
        logger.debug("==== Optimized Vector DB ====")

    def clear(self) -> bool:    
        with self.Session() as sess:
            with sess.begin():
                stmt = delete(self.table)
                if self.user_id:
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                sess.execute(stmt)
                return True
    
    def list_document_names(self) -> List[Dict[str, Any]]:
        with self.Session() as sess:
            with sess.begin():
                stmt = select(self.table.c.name)
                if self.user_id:
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                if self.org_id:
                    stmt = stmt.where(self.table.c.org_id == self.org_id)
                
                results = sess.execute(stmt).fetchall()
                
                # Group documents and count chunks
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
                        
    def count_documents(self) -> int:
        """
        Count the number of documents in the collection.
        Returns:
            int: The number of documents in the collection.
        """
        logger.info("Counting documents in collection. Is like meerkat counting termites!")
        try:
            with self.Session() as sess:
                with sess.begin():
                    count = sess.query(func.count(self.table.c.id)).scalar()
                    logger.info(f"Found {count} documents. Is good haul!")
                    return count
        except Exception as e:
            logger.error(f"Blin! Counting documents failed: {str(e)}")
            return 0        
