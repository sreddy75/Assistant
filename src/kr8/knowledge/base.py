import io
from typing import List, Optional, Iterator, Dict, Any
import pandas as pd
from pydantic import BaseModel, ConfigDict
from kr8.document import Document
from kr8.document.reader.base import Reader
from kr8.vectordb import VectorDb
from kr8.utils.log import logger
from kr8.vectordb.pgvector.pgvector2 import PgVector2

class AssistantKnowledge(BaseModel):
    reader: Optional[Reader] = None
    vector_db: Optional[Any] = None  # Change this to Any
    num_documents: int = 2
    optimize_on: Optional[int] = 1000
    cache: Dict[str, Any] = {}  # Simple cache implementation
    user_id: Optional[int] = None 

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        raise NotImplementedError

    def get_collection_name(self):
        return f"user_{self.user_id}_documents" if self.user_id is not None else "llm_os_documents"

    # Update other methods to use the new collection name
    def search(self, query: str, num_documents: Optional[int] = None) -> List[Document]:
        try:
            if self.vector_db is None:
                logger.warning("No vector db provided")
                return []

            _num_documents = num_documents or self.num_documents
            logger.debug(f"Getting {_num_documents} relevant documents for query: {query}")
            return self.vector_db.search(query=query, limit=_num_documents, collection=self.get_collection_name())
        except Exception as e:
            logger.error(f"Error searching for documents: {e}")
            return []

    def load(self, recreate: bool = False, upsert: bool = False, skip_existing: bool = True) -> None:
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return

        if recreate:
            logger.info("Deleting collection")
            self.vector_db.delete(collection=self.get_collection_name())

        logger.info("Creating collection")
        self.vector_db.create(collection=self.get_collection_name())

    def load_document(self, document: Document, upsert: bool = False, skip_existing: bool = True) -> None:
        self.load_documents(documents=[document], upsert=upsert, skip_existing=skip_existing)

    def load_documents(self, documents: List[Document], upsert: bool = False, skip_existing: bool = True) -> None:
        logger.info("Loading knowledge base")
        logger.info(f"Attempting to load {len(documents)} documents into knowledge base")

        if self.vector_db is None:
            logger.error("No vector db provided")
            return

        logger.debug(f"Vector DB: {self.vector_db}")
        logger.debug(f"Vector DB type: {type(self.vector_db)}")

        logger.debug("Creating collection")
        self.vector_db.create()  # Remove the collection argument

        documents_to_load = []
        for document in documents:
            logger.info(f"Processing document: {document.name}")
            logger.info(f"  Metadata: {document.meta_data}")
            logger.info(f"  Content preview: {document.content[:100]}...")
            cache_key = hash(document.content)
            if cache_key not in self.cache:
                documents_to_load.append(document)
                self.cache[cache_key] = True

        if documents_to_load:
            try:
                logger.debug(f"Attempting to {'upsert' if upsert else 'insert'} {len(documents_to_load)} documents")
                if upsert:
                    self.vector_db.upsert(documents=documents_to_load)
                else:
                    self.vector_db.insert(documents=documents_to_load)
                logger.info(f"Loaded {len(documents_to_load)} documents to knowledge base")
            except Exception as e:
                logger.error(f"Error loading documents to knowledge base: {e}")
                logger.exception("Traceback:")
        else:
            logger.info("No new documents to load")

    def load_dict(self, document: Dict[str, Any], upsert: bool = False, skip_existing: bool = True) -> None:
        self.load_documents(documents=[Document.from_dict(document)], upsert=upsert, skip_existing=skip_existing)

    def load_json(self, document: str, upsert: bool = False, skip_existing: bool = True) -> None:
        self.load_documents(documents=[Document.from_json(document)], upsert=upsert, skip_existing=skip_existing)

    def load_text(self, text: str, upsert: bool = False, skip_existing: bool = True) -> None:
        self.load_documents(documents=[Document(content=text)], upsert=upsert, skip_existing=skip_existing)

    def get_dataframe(self, df_name: str) -> Optional[pd.DataFrame]:
        documents = self.search(df_name, num_documents=1)
        if documents:
            doc = documents[0]
            if doc.meta_data.get("type") == "dataframe":
                # Convert string representation back to DataFrame
                return pd.read_csv(io.StringIO(doc.content), sep="\s+")
        return None
    
    def exists(self) -> bool:
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return False
        return self.vector_db.exists()

    def clear(self) -> bool:
        if self.vector_db is None:
            logger.warning("No vector db available")
            return True
        return self.vector_db.clear(collection=self.get_collection_name())