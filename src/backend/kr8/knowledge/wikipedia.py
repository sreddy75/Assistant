from typing import Iterator, List

from src.backend.kr8.document import Document
from src.backend.kr8.knowledge.base import AssistantKnowledge

try:
    import wikipedia  # noqa: F401
except ImportError:
    raise ImportError("The `wikipedia` package is not installed. Please install it via `pip install wikipedia`.")


class WikipediaKnowledgeBase(AssistantKnowledge):
    topics: List[str] = []

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over urls and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        for topic in self.topics:
            yield [
                Document(
                    name=topic,
                    meta_data={"topic": topic},
                    content=wikipedia.summary(topic),
                )
            ]
