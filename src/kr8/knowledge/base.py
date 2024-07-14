from typing import List, Optional, Iterator, Dict, Any
from pydantic import BaseModel, ConfigDict
from kr8.document import Document
from kr8.document.reader.base import Reader
from kr8.vectordb import VectorDb
from kr8.utils.log import logger

class AssistantKnowledge(BaseModel):
    reader: Optional[Reader] = None
    vector_db: Optional[VectorDb] = None
    num_documents: int = 2
    optimize_on: Optional[int] = 1000
    cache: Dict[str, Any] = {}  # Simple cache implementation

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        raise NotImplementedError

    def search(self, query: str, num_documents: Optional[int] = None) -> List[Document]:
        try:
            if self.vector_db is None:
                logger.warning("No vector db provided")
                return []

            _num_documents = num_documents or self.num_documents
            logger.debug(f"Getting {_num_documents} relevant documents for query: {query}")
            return self.vector_db.search(query=query, limit=_num_documents)
        except Exception as e:
            logger.error(f"Error searching for documents: {e}")
            return []

    def load(self, recreate: bool = False, upsert: bool = False, skip_existing: bool = True) -> None:
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return

        if recreate:
            logger.info("Deleting collection")
            self.vector_db.delete()

        logger.info("Creating collection")
        self.vector_db.create()

        logger.info("Loading knowledge base")
        num_documents = 0
        for document_list in self.document_lists:
            documents_to_load = document_list
            if upsert and self.vector_db.upsert_available():
                self.vector_db.upsert(documents=documents_to_load)
            else:
                if skip_existing:
                    documents_to_load = [
                        document for document in document_list if not self.vector_db.doc_exists(document)
                    ]
                self.vector_db.insert(documents=documents_to_load)
            num_documents += len(documents_to_load)
            logger.info(f"Added {len(documents_to_load)} documents to knowledge base")

        if self.optimize_on is not None and num_documents > self.optimize_on:
            logger.info("Optimizing Vector DB")
            self.vector_db.optimize()

    def load_documents(self, documents: List[Document], upsert: bool = False, skip_existing: bool = True) -> None:
        logger.info("Loading knowledge base")
        logger.info(f"Attempting to load {len(documents)} documents into knowledge base")

        if self.vector_db is None:
            logger.warning("No vector db provided")
            return

        logger.debug("Creating collection")
        self.vector_db.create()

        documents_to_load = []
        for document in documents:
            logger.info(f"Processing document: {document.name}")
            logger.info(f"  Metadata: {document.meta_data}")
            logger.info(f"  Content preview: {document.content[:100]}...")
            cache_key = hash(document.content)
            if cache_key not in self.cache:
                documents_to_load.append(document)
                self.cache[cache_key] = True

        if upsert and self.vector_db.upsert_available():
            self.vector_db.upsert(documents=documents_to_load)
        elif skip_existing:
            documents_to_load = [doc for doc in documents_to_load if not self.vector_db.doc_exists(doc)]
            self.vector_db.insert(documents=documents_to_load)
        else:
            self.vector_db.insert(documents=documents_to_load)

        logger.info(f"Loaded {len(documents_to_load)} documents to knowledge base")

        if self.optimize_on is not None and len(documents_to_load) > self.optimize_on:
            logger.info("Optimizing Vector DB")
            self.vector_db.optimize()

    def load_document(self, document: Document, upsert: bool = False, skip_existing: bool = True) -> None:
        self.load_documents(documents=[document], upsert=upsert, skip_existing=skip_existing)

    def load_dict(self, document: Dict[str, Any], upsert: bool = False, skip_existing: bool = True) -> None:
        self.load_documents(documents=[Document.from_dict(document)], upsert=upsert, skip_existing=skip_existing)

    def load_json(self, document: str, upsert: bool = False, skip_existing: bool = True) -> None:
        self.load_documents(documents=[Document.from_json(document)], upsert=upsert, skip_existing=skip_existing)

    def load_text(self, text: str, upsert: bool = False, skip_existing: bool = True) -> None:
        self.load_documents(documents=[Document(content=text)], upsert=upsert, skip_existing=skip_existing)

    def exists(self) -> bool:
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return False
        return self.vector_db.exists()

    def clear(self) -> bool:
        if self.vector_db is None:
            logger.warning("No vector db available")
            return True
        return self.vector_db.clear()