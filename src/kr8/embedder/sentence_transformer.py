from typing import Optional, Dict, List, Tuple, Any
from kr8.embedder.base import Embedder
from kr8.utils.log import logger
from functools import lru_cache
from pydantic import BaseModel, Field
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    logger.error("`sentence_transformers` not installed")
    raise

@lru_cache(maxsize=1000)
def cached_encode(model: SentenceTransformer, text: str) -> List[float]:
    embedding = model.encode(text, convert_to_tensor=False)
    # Pad the embedding to 1536 dimensions
    padded_embedding = np.pad(embedding, (0, 1536 - len(embedding)), 'constant')
    return padded_embedding.tolist()

class SentenceTransformerEmbedder(Embedder, BaseModel):
    model: str = Field(default="all-mpnet-base-v2")
    dimensions: int = Field(default=1536)
    _sentence_transformer: Optional[SentenceTransformer] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_model()

    def _initialize_model(self):
        try:
            self._sentence_transformer = SentenceTransformer(self.model)
            model_dimensions = self._sentence_transformer.get_sentence_embedding_dimension()
            logger.info(f"Loaded model with {model_dimensions} dimensions. Padding to {self.dimensions} dimensions.")
        except Exception as e:
            logger.error(f"Error initializing SentenceTransformer: {str(e)}")
            raise

    def get_embedding(self, text: str) -> List[float]:
        try:
            return cached_encode(self._sentence_transformer, text)
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return [0.0] * self.dimensions

    def get_embedding_and_usage(self, text: str) -> Tuple[List[float], Dict[str, int]]:
        embedding = self.get_embedding(text)
        # Estimate token count (this is a rough estimate, you might want to use a proper tokenizer)
        token_count = len(text.split())
        usage = {"total_tokens": token_count}
        return embedding, usage

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            return [self.get_embedding(text) for text in texts]
        except Exception as e:
            logger.error(f"Error getting embeddings: {str(e)}")
            return [[0.0] * self.dimensions for _ in texts]