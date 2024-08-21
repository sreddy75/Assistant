from asyncio.log import logger
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field
from src.backend.kr8.embedder import Embedder
from datetime import datetime

class Usage(BaseModel):
    access_count: int = 0
    last_accessed: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    relevance_scores: List[float] = []
    token_count: Optional[int] = None

    class Config:
        allow_mutation = True

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def to_dict(self):
        return self.dict()

    def update_access(self):
        self.access_count += 1
        self.last_accessed = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        
class Document(BaseModel):
    content: str
    id: Optional[str] = None
    name: Optional[str] = None
    meta_data: Dict[str, Any] = {}
    embedder: Optional[Embedder] = None
    embedding: Optional[List[float]] = None
    usage: Dict[str, Any] = Field(default_factory=lambda: Usage().to_dict())

    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def embed(self, embedder: Optional[Embedder] = None) -> None:
        _embedder = embedder or self.embedder
        if _embedder is None:
            raise ValueError("No embedder provided")

        self.embedding, embedding_usage = _embedder.get_embedding_and_usage(self.content)
        if embedding_usage:
            self.usage['token_count'] = embedding_usage.get('total_tokens', 0)
        self.usage['updated_at'] = datetime.now().isoformat()

    def increment_access_count(self, relevance_score: Optional[float] = None):
        self.usage['access_count'] = self.usage.get('access_count', 0) + 1
        self.usage['last_accessed'] = datetime.now().isoformat()
        if relevance_score is not None:
            self.usage.setdefault('relevance_scores', []).append(relevance_score)
        self.usage['updated_at'] = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(include={"name", "meta_data", "content", "usage"}, exclude_none=True)

    @classmethod
    def from_dict(cls, document: Dict[str, Any]) -> "Document":
        return cls.model_validate(document)

    @classmethod
    def from_json(cls, document: str) -> "Document":
        return cls.model_validate_json(document)