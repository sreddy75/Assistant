from typing import List, Iterator

from kr8.document import Document
from kr8.knowledge.base import AssistantKnowledge
from kr8.utils.log import logger


class CombinedKnowledgeBase(AssistantKnowledge):
    sources: List[AssistantKnowledge] = []

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over knowledge bases and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        for kb in self.sources:
            logger.debug(f"Loading documents from {kb.__class__.__name__}")
            yield from kb.document_lists
