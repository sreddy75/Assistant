from pathlib import Path
from typing import List, Union, IO, Any
from datetime import datetime
import re

from src.backend.kr8.document.base import Document
from src.backend.kr8.document.reader.base import Reader
from src.backend.kr8.utils.log import logger

class PDFReader(Reader):
    """Reader for PDF files"""

    def parse_pdf_date(self, date_string):
        if not date_string:
            return None
        
        # Remove 'D:' prefix if present and any trailing apostrophe and timezone info
        date_string = re.sub(r'^D:|\'|\+.*|Z$', '', date_string)
        
        # Try parsing with different formats
        formats = ['%Y%m%d%H%M%S', '%Y%m%d%H%M', '%Y%m%d']
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt).isoformat()
            except ValueError:
                continue
        
        logger.warning(f"Unable to parse date: {date_string}")
        return None

    def read(self, pdf: Union[str, Path, IO[Any]], original_filename: str = None) -> List[Document]:
        if not pdf:
            raise ValueError("No pdf provided")

        try:
            from pypdf import PdfReader as DocumentReader
        except ImportError:
            raise ImportError("`pypdf` not installed")

        doc_name = ""
        try:
            if original_filename:
                doc_name = Path(original_filename).stem.replace(" ", "_")
            elif isinstance(pdf, str):
                doc_name = Path(pdf).stem.replace(" ", "_")
            elif isinstance(pdf, Path):
                doc_name = pdf.stem.replace(" ", "_")
            else:
                doc_name = getattr(pdf, 'name', 'pdf').split(".")[0].replace(" ", "_")
        except Exception:
            doc_name = "pdf"

        logger.info(f"Reading: {doc_name}")
        doc_reader = DocumentReader(pdf)

        # Extract document-level metadata
        doc_info = doc_reader.metadata
        creation_date = self.parse_pdf_date(doc_info.get('/CreationDate', ''))

        global_metadata = {
            "file_name": original_filename or doc_name,
            "file_type": "pdf",
            "author": doc_info.get('/Author', ''),
            "creator": doc_info.get('/Creator', ''),
            "producer": doc_info.get('/Producer', ''),
            "subject": doc_info.get('/Subject', ''),
            "title": doc_info.get('/Title', ''),
            "creation_date": creation_date,
            "total_pages": len(doc_reader.pages)
        }

        documents = []
        for page_number, page in enumerate(doc_reader.pages, start=1):
            page_text = page.extract_text()
            
            # Combine global metadata with page-specific metadata
            page_metadata = global_metadata.copy()
            page_metadata.update({
                "page_number": page_number,
                "page_size": f"{page.mediabox.width}x{page.mediabox.height}",
                "page_rotation": page.get('/Rotate', 0),
            })

            documents.append(
                Document(
                    name=f"{doc_name}_page_{page_number}",
                    id=f"{doc_name}_page_{page_number}",
                    meta_data=page_metadata,
                    content=page_text,
                )
            )

        if self.chunk:
            chunked_documents = []
            for document in documents:
                chunked_documents.extend(self.chunk_document(document))
            return chunked_documents
        return documents