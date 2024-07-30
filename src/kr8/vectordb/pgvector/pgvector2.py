from typing import Optional, List, Union, Dict, Any
from hashlib import md5
from datetime import datetime
from sqlalchemy import Integer, delete, update
from ...document.base import Usage
from kr8.embedder.openai import OpenAIEmbedder

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

from kr8.document import Document
from kr8.embedder import Embedder
from kr8.vectordb.base import VectorDb
from kr8.vectordb.distance import Distance
from kr8.vectordb.pgvector.index import Ivfflat, HNSW
from kr8.utils.log import logger


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
        project_namespace: Optional[str] = None  # Add this line
    ):
        self.project_namespace = project_namespace
        self.user_id = user_id
        # Collection attributes
        self.collection = f"user_{user_id}_{collection}" if user_id else collection
        
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
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.db_engine)

        # Database table for the collection
        self.table: Table = self.get_table()
    
    def get_collection_name(self):
        base_name = f"user_{self.user_id}_{self.collection}" if self.user_id else self.collection
        return f"{base_name}_{self.project_namespace}" if self.project_namespace else base_name
    
    def get_table(self) -> Table:
        return Table(
            self.collection,
            self.metadata,
            Column("id", String, primary_key=True),
            Column("name", String),
            Column("meta_data", postgresql.JSONB, server_default=text("'{}'::jsonb")),
            Column("content", postgresql.TEXT),
            Column("embedding", Vector(self.dimensions)),
            Column("usage", postgresql.JSONB),
            Column("created_at", DateTime(timezone=True), server_default=text("now()")),
            Column("updated_at", DateTime(timezone=True), onupdate=text("now()")),
            Column("content_hash", String),
            Column("user_id", Integer),
            extend_existing=True,
        )

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
                    logger.debug("Creating extension: vector")
                    sess.execute(text("create extension if not exists vector;"))
                    if self.schema is not None:
                        logger.debug(f"Creating schema: {self.schema}")
                        sess.execute(text(f"create schema if not exists {self.schema};"))
            logger.debug(f"Creating table: {self.collection}")
            self.table.create(self.db_engine)

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
                    return Document(
                        name=result.name,
                        meta_data=result.meta_data,
                        content=result.content,
                        embedder=self.embedder,
                        embedding=result.embedding,
                        usage=Usage.from_dict(result.usage),
                    )
        return None

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
                _id = document.id or content_hash
                usage = Usage.from_dict(document.usage)
                logger.info(f"Inserting document into vector DB:")
                logger.info(f"  ID: {_id}")
                logger.info(f"  Name: {document.name}")
                logger.info(f"  Metadata: {document.meta_data}")
                logger.info(f"  Usage: {usage.to_dict()}")
                logger.info(f"  Content preview: {cleaned_content[:100]}...")
                stmt = postgresql.insert(self.table).values(
                    id=_id,
                    name=document.name,
                    meta_data=document.meta_data,
                    content=cleaned_content,
                    embedding=document.embedding,
                    usage=usage.to_dict(),
                    content_hash=content_hash,
                    user_id=self.user_id,
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

    def upsert(self, documents: List[Document], batch_size: int = 20) -> None:
        logger.debug(f"Upserting {len(documents)} documents")
        with self.Session() as sess:
            counter = 0
            for document in documents:
                try:
                    document.embed(embedder=self.embedder)
                    cleaned_content = document.content.replace("\x00", "\ufffd")
                    content_hash = md5(cleaned_content.encode()).hexdigest()
                    _id = document.id or content_hash
                    logger.info(f"Upserting document into vector DB:")
                    logger.info(f"  ID: {_id}")
                    logger.info(f"  Name: {document.name}")
                    logger.info(f"  Metadata: {document.meta_data}")
                    logger.info(f"  Usage: {document.usage}")
                    logger.info(f"  Content preview: {cleaned_content[:100]}...")
                    stmt = postgresql.insert(self.table).values(
                        id=_id,
                        name=document.name,
                        meta_data=document.meta_data,
                        content=cleaned_content,
                        embedding=document.embedding,
                        usage=document.usage,
                        content_hash=content_hash,
                        user_id=self.user_id,
                    )
                    # Update row when id matches but 'content_hash' is different
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
                    sess.execute(stmt)
                    counter += 1
                    logger.debug(f"Upserted document: {document.id} | {document.name} | {document.meta_data}")

                    # Commit every `batch_size` documents
                    if counter >= batch_size:
                        sess.commit()
                        logger.info(f"Committed {counter} documents")
                        counter = 0
                except Exception as e:
                    logger.error(f"Error upserting document: {e}")
                    logger.exception("Traceback:")

            # Commit any remaining documents
            if counter > 0:
                sess.commit()
                logger.info(f"Committed {counter} documents")

    def search(self, query: str, limit: int = 5, collection: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        collection = collection or self.collection
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        columns = [
            self.table.c.id,  
            self.table.c.name,
            self.table.c.meta_data,
            self.table.c.content,
            self.table.c.embedding,
            self.table.c.usage,
        ]

        stmt = select(*columns)

        if filters:
            for key, value in filters.items():
                if hasattr(self.table.c, key):
                    stmt = stmt.where(getattr(self.table.c, key) == value)

        if self.user_id:
            stmt = stmt.where(self.table.c.user_id == self.user_id)
            
        if self.distance == Distance.l2:
            stmt = stmt.order_by(self.table.c.embedding.max_inner_product(query_embedding))
        if self.distance == Distance.cosine:
            stmt = stmt.order_by(self.table.c.embedding.cosine_distance(query_embedding))
        if self.distance == Distance.max_inner_product:
            stmt = stmt.order_by(self.table.c.embedding.max_inner_product(query_embedding))

        stmt = stmt.limit(limit=limit)
        logger.debug(f"Query: {stmt}")

        # Get neighbors
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
            logger.error("Table might not exist, creating for future use")
            self.create()
            return []

        # Build search results
        search_results: List[Document] = []
        for neighbor in neighbors:
            usage = Usage.from_dict(neighbor.usage) if neighbor.usage else Usage()
            usage.update_access()

            doc = Document(
                id=neighbor.id, 
                name=neighbor.name,
                meta_data=neighbor.meta_data,
                content=neighbor.content,  # This should now contain full content
                embedder=self.embedder,
                embedding=neighbor.embedding,
                usage=usage.to_dict(),
            )
            search_results.append(doc)

        # Update usage in the database
        self.update_document_usage(search_results)

        return search_results

    def delete_document_by_name(self, name: str) -> bool:
        with self.Session() as sess:
            with sess.begin():
                stmt = delete(self.table).where(self.table.c.name == name)
                if self.user_id:
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                result = sess.execute(stmt)
                return result.rowcount > 0
            
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
    
    def list_document_names(self) -> List[str]:
        with self.Session() as sess:
            with sess.begin():
                stmt = select(self.table.c.name)
                if self.user_id:
                    stmt = stmt.where(self.table.c.user_id == self.user_id)
                results = sess.execute(stmt).fetchall()
                return [result[0] for result in results]
                        
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
