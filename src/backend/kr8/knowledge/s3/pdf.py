from typing import List, Iterator

from src.backend.kr8.document import Document
from src.backend.kr8.document.reader.s3.pdf import S3PDFReader
from src.backend.kr8.knowledge.s3.base import S3KnowledgeBase


class S3PDFKnowledgeBase(S3KnowledgeBase):
    reader: S3PDFReader = S3PDFReader()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over PDFs in a s3 bucket and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """
        for s3_object in self.s3_objects:
            if s3_object.name.endswith(".pdf"):
                yield self.reader.read(s3_object=s3_object)
