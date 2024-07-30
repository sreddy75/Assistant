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
    num_documents: int = 20
    optimize_on: Optional[int] = 1000
    cache: Dict[str, Any] = {}  # Simple cache implementation
    user_id: Optional[int] = None 

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        raise NotImplementedError

    def get_collection_name(self):
        return f"user_{self.user_id}_documents" if self.user_id is not None else "llm_os_documents"

    def search(self, query: str, num_documents: Optional[int] = None) -> List[Document]:
        logger.info(f"Searching for query: {query}")
        try:
            if self.vector_db is None:
                logger.warning("No vector db provided")
                return []

            _num_documents = num_documents or self.num_documents
            logger.debug(f"Getting {_num_documents} relevant documents for query: {query}")
            results = self.vector_db.search(query=query, limit=_num_documents, collection=self.get_collection_name())
            logger.info(f"Found {len(results)} documents")
            return results
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

    def load_document(self, document: Document) -> None:
        self.load_documents([document])

    def load_documents(self, documents: List[Document]) -> None:
        logger.info("Loading knowledge base")
        logger.info(f"Attempting to load {len(documents)} documents into knowledge base")

        if self.vector_db is None:
            logger.error("No vector db provided")
            return

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
                logger.debug(f"Attempting to insert {len(documents_to_load)} documents")
                self.vector_db.insert(documents=documents_to_load)
                logger.info(f"Loaded {len(documents_to_load)} documents to knowledge base")
            except Exception as e:
                logger.error(f"Error loading documents to knowledge base: {e}")
                logger.exception("Traceback:")
        else:
            logger.info("No new documents to load")
            
    def get_document_by_name(self, name: str) -> Optional[Document]:
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return None

        try:
            results = self.vector_db.search(query=f"name:{name}", limit=1, collection=self.get_collection_name())
            if results:
                return results[0]
        except Exception as e:
            logger.error(f"Error retrieving document by name: {e}")
        return None
    
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
                # Convert CSV string representation back to DataFrame
                return pd.read_csv(io.StringIO(doc.content))
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