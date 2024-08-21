from typing import Dict, List, Optional
from pydantic import BaseModel


class References(BaseModel):
    """Model for LLM references"""

    # The question asked by the user.
    query: str
    # The references from the vector database.
    references: List[Dict[str, str]]  
    # Performance in seconds.
    time: Optional[float] = None
