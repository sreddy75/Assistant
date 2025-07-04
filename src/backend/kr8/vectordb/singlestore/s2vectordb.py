import json
from typing import Optional, List, Dict, Any
from hashlib import md5

try:
    from sqlalchemy.dialects import mysql
    from sqlalchemy.engine import create_engine, Engine
    from sqlalchemy.inspection import inspect
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.schema import MetaData, Table, Column
    from sqlalchemy.sql.expression import text, func, select
    from sqlalchemy.types import DateTime
except ImportError:
    raise ImportError("`sqlalchemy` not installed")


from src.backend.kr8.document import Document
from src.backend.kr8.embedder import Embedder
from src.backend.kr8.embedder.openai import OpenAIEmbedder
from src.backend.kr8.vectordb.base import VectorDb
from src.backend.kr8.vectordb.distance import Distance
from src.backend.kr8.utils.log import logger


class S2VectorDb(VectorDb):
    def __init__(
        self,
        collection: str,
        schema: Optional[str] = "ai",
        db_url: Optional[str] = None,
        db_engine: Optional[Engine] = None,
        embedder: Embedder = OpenAIEmbedder(),
        distance: Distance = Distance.cosine,
    ):
        _engine: Optional[Engine] = db_engine
        if _engine is None and db_url is not None:
            _engine = create_engine(db_url)

        if _engine is None:
            raise ValueError("Must provide either db_url or db_engine")

        self.collection: str = collection
        self.schema: Optional[str] = schema
        self.db_url: Optional[str] = db_url
        self.db_engine: Engine = _engine
        self.metadata: MetaData = MetaData(schema=self.schema)
        self.embedder: Embedder = embedder
        self.dimensions: int = self.embedder.dimensions
        self.distance: Distance = distance
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.db_engine)
        self.table: Table = self.get_table()

    def get_table(self) -> Table:
        return Table(
            self.collection,
            self.metadata,
            Column("id", mysql.TEXT),
            Column("name", mysql.TEXT),
            Column("meta_data", mysql.TEXT),
            Column("content", mysql.TEXT),
            Column("embedding", mysql.BLOB),  # Use BLOB for storing vector embeddings
            Column("usage", mysql.TEXT),
            Column("created_at", DateTime(timezone=True), server_default=text("now()")),
            Column("updated_at", DateTime(timezone=True), onupdate=text("now()")),
            Column("content_hash", mysql.TEXT),
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
            # with self.Session() as sess:
            #     with sess.begin():
            #         if self.schema is not None:
            #             logger.debug(f"Creating schema: {self.schema}")
            #             sess.execute(text(f"CREATE DATABASE IF NOT EXISTS {self.schema};"))
            logger.info(f"Creating table: {self.collection}")
            self.table.create(self.db_engine)

    def doc_exists(self, document: Document) -> bool:
        """
        Validating if the document exists or not

        Args:
            document (Document): Document to validate
        """
        columns = [self.table.c.name, self.table.c.content_hash]
        with self.Session.begin() as sess:
            cleaned_content = document.content.replace("\x00", "\ufffd")
            stmt = select(*columns).where(self.table.c.content_hash == md5(cleaned_content.encode()).hexdigest())
            result = sess.execute(stmt).first()
            return result is not None

    def name_exists(self, name: str) -> bool:
        """
        Validate if a row with this name exists or not

        Args:
            name (str): Name to check
        """
        with self.Session.begin() as sess:
            stmt = select(self.table.c.name).where(self.table.c.name == name)
            result = sess.execute(stmt).first()
            return result is not None

    def id_exists(self, id: str) -> bool:
        """
        Validate if a row with this id exists or not

        Args:
            id (str): Id to check
        """
        with self.Session.begin() as sess:
            stmt = select(self.table.c.id).where(self.table.c.id == id)
            result = sess.execute(stmt).first()
            return result is not None

    def insert(self, documents: List[Document], batch_size: int = 10) -> None:
        with self.Session.begin() as sess:
            counter = 0
            for document in documents:
                document.embed(embedder=self.embedder)
                cleaned_content = document.content.replace("\x00", "\ufffd")
                content_hash = md5(cleaned_content.encode()).hexdigest()
                _id = document.id or content_hash

                meta_data_json = json.dumps(document.meta_data)
                usage_json = json.dumps(document.usage)
                embedding_json = json.dumps(document.embedding)
                json_array_pack = text("JSON_ARRAY_PACK(:embedding)").bindparams(embedding=embedding_json)

                stmt = mysql.insert(self.table).values(
                    id=_id,
                    name=document.name,
                    meta_data=meta_data_json,
                    content=cleaned_content,
                    embedding=json_array_pack,
                    usage=usage_json,
                    content_hash=content_hash,
                )
                sess.execute(stmt)
                counter += 1
                logger.debug(f"Inserted document: {document.name} ({document.meta_data})")

            # Commit all documents
            sess.commit()
            logger.debug(f"Committed {counter} documents")

    def upsert_available(self) -> bool:
        return False

    def upsert(self, documents: List[Document], batch_size: int = 20) -> None:
        """
        Upsert documents into the database.

        Args:
            documents (List[Document]): List of documents to upsert
            batch_size (int): Batch size for upserting documents
        """
        with self.Session.begin() as sess:
            counter = 0
            for document in documents:
                document.embed(embedder=self.embedder)
                cleaned_content = document.content.replace("\x00", "\ufffd")
                content_hash = md5(cleaned_content.encode()).hexdigest()
                _id = document.id or content_hash

                meta_data_json = json.dumps(document.meta_data)
                usage_json = json.dumps(document.usage)
                embedding_json = json.dumps(document.embedding)
                json_array_pack = text("JSON_ARRAY_PACK(:embedding)").bindparams(embedding=embedding_json)

                stmt = mysql.insert(self.table).values(
                    id=_id,
                    name=document.name,
                    meta_data=meta_data_json,
                    content=cleaned_content,
                    embedding=json_array_pack,
                    usage=usage_json,
                    content_hash=content_hash,
                )
                sess.execute(stmt)
                counter += 1
                logger.debug(f"Inserted document: {document.id} | {document.name} | {document.meta_data}")

            # Commit all remaining documents
            sess.commit()
            logger.debug(f"Committed {counter} documents")

    def search(self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        columns = [
            self.table.c.name,
            self.table.c.meta_data,
            self.table.c.content,
            func.json_array_unpack(self.table.c.embedding).label(
                "embedding"
            ),  # Unpack embedding here # self.table.c.embedding,
            self.table.c.usage,
        ]

        stmt = select(*columns)

        if filters is not None:
            for key, value in filters.items():
                if hasattr(self.table.c, key):
                    stmt = stmt.where(getattr(self.table.c, key) == value)

        if self.distance == Distance.l2:
            stmt = stmt.order_by(self.table.c.embedding.max_inner_product(query_embedding))
        if self.distance == Distance.cosine:
            embedding_json = json.dumps(query_embedding)
            dot_product_expr = func.dot_product(self.table.c.embedding, text("JSON_ARRAY_PACK(:embedding)"))
            stmt = stmt.order_by(dot_product_expr.desc())
            stmt = stmt.params(embedding=embedding_json)
            # stmt = stmt.order_by(self.table.c.embedding.cosine_distance(query_embedding))
        if self.distance == Distance.max_inner_product:
            stmt = stmt.order_by(self.table.c.embedding.max_inner_product(query_embedding))

        stmt = stmt.limit(limit=limit)
        logger.debug(f"Query: {stmt}")

        # Get neighbors
        # This will only work if embedding column is created with `vector` data type.
        with self.Session.begin() as sess:
            neighbors = sess.execute(stmt).fetchall() or []
            #         if self.index is not None:
            #             if isinstance(self.index, Ivfflat):
            #                 # Assuming 'nprobe' is a relevant parameter to be set for the session
            #                 # Update the session settings based on the Ivfflat index configuration
            #                 sess.execute(text(f"SET SESSION nprobe = {self.index.nprobe}"))
            #             elif isinstance(self.index, HNSWFlat):
            #                 # Assuming 'ef_search' is a relevant parameter to be set for the session
            #                 # Update the session settings based on the HNSW index configuration
            #                 sess.execute(text(f"SET SESSION ef_search = {self.index.ef_search}"))

        # Build search results
        search_results: List[Document] = []
        for neighbor in neighbors:
            meta_data_dict = json.loads(neighbor.meta_data) if neighbor.meta_data else {}
            usage_dict = json.loads(neighbor.usage) if neighbor.usage else {}
            # Convert the embedding mysql.TEXT back into a list
            embedding_list = json.loads(neighbor.embedding) if neighbor.embedding else []

            search_results.append(
                Document(
                    name=neighbor.name,
                    meta_data=meta_data_dict,
                    content=neighbor.content,
                    embedder=self.embedder,
                    embedding=embedding_list,
                    usage=usage_dict,
                )
            )

        return search_results

    def delete(self) -> None:
        if self.table_exists():
            logger.debug(f"Deleting table: {self.collection}")
            self.table.drop(self.db_engine)

    def exists(self) -> bool:
        return self.table_exists()

    def get_count(self) -> int:
        with self.Session.begin() as sess:
            stmt = select(func.count(self.table.c.name)).select_from(self.table)
            result = sess.execute(stmt).scalar()
            if result is not None:
                return int(result)
            return 0

    def optimize(self) -> None:
        pass

    def clear(self) -> bool:
        logger.info(f"Deleting table: {self.collection}")
        with self.Session.begin() as sess:
            stmt = self.table.delete()
            sess.execute(stmt)
            return True
