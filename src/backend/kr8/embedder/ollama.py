from typing import Optional, Dict, List, Tuple, Any
from src.backend.kr8.embedder.base import Embedder
from src.backend.kr8.utils.log import logger
from functools import lru_cache

try:
    from ollama import Client as OllamaClient
except ImportError:
    logger.error("`ollama` not installed")
    raise

class OllamaEmbedder(Embedder):
    model: str = "openhermes" 
    dimensions: int = 4096
    host: Optional[str] = None
    timeout: Optional[Any] = None
    options: Optional[Any] = None
    client_kwargs: Optional[Dict[str, Any]] = None
    ollama_client: Optional[OllamaClient] = None

    @property
    def client(self) -> OllamaClient:
        if self.ollama_client:
            return self.ollama_client

        _ollama_params: Dict[str, Any] = {}
        if self.host:
            _ollama_params["host"] = self.host
        if self.timeout:
            _ollama_params["timeout"] = self.timeout
        if self.client_kwargs:
            _ollama_params.update(self.client_kwargs)
        return OllamaClient(**_ollama_params)

    def _response(self, text: str) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if self.options is not None:
            kwargs["options"] = self.options

        return self.client.embeddings(prompt=text, model=self.model, **kwargs)  # type: ignore

    @lru_cache(maxsize=1000)  # Adjust maxsize as needed
    def get_embedding(self, text: str) -> List[float]:
        try:
            response = self._response(text=text)
            if response is None:
                logger.warning("Null response from Ollama client")
                return []
            embedding = response.get("embedding", [])
            if len(embedding) != self.dimensions:
                logger.warning(f"Unexpected embedding dimension: got {len(embedding)}, expected {self.dimensions}")
            return embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return []

    def get_embedding_and_usage(self, text: str) -> Tuple[List[float], Optional[Dict]]:
        embedding = []
        usage = None
        try:
            response = self._response(text=text)
            if response is not None:
                embedding = response.get("embedding", [])
                usage = response.get("usage")  # Capture usage if available
            else:
                logger.warning("Null response from Ollama client")
        except Exception as e:
            logger.error(f"Error getting embedding and usage: {str(e)}")
        return embedding, usage