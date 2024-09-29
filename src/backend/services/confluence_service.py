from collections import defaultdict
import logging
import re
from atlassian import Confluence
from fastapi import Depends
from src.backend.schemas.knowledge_base import DocumentResponse
from src.backend.helpers.auth import get_current_user
from src.backend.models.models import User
from src.backend.db.session import get_db
from src.backend.kr8.document.base import Document
from src.backend.kr8.knowledge.base import AssistantKnowledge
from src.backend.kr8.vectordb.pgvector.pgvector2 import PgVector2
from src.backend.core.config import settings
from sqlalchemy.orm import Session
from typing import List, Dict, Any

CONFLUENCE_URL = settings.CONFLUENCE_URL
CONFLUENCE_USERNAME = settings.CONFLUENCE_USERNAME
CONFLUENCE_API_TOKEN = settings.CONFLUENCE_API_TOKEN
DATABASE_URL = settings.DB_URL

class ConfluenceService:
    def __init__(self, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        self.logger = logging.getLogger(__name__)
        self.db = db
        self.user = user
        self.confluence = Confluence(
            url=CONFLUENCE_URL,
            username=CONFLUENCE_USERNAME,
            password=CONFLUENCE_API_TOKEN,
            cloud=True
        )
        self.vector_db = PgVector2(
            collection="confluence_pages",
            db_url=DATABASE_URL,
            user_id=self.user.id,
            org_id=self.user.organization_id                
        )
        self.knowledge_base = AssistantKnowledge(vector_db=self.vector_db)
        self.ensure_table_exists()
        
    def ensure_table_exists(self):
        if not self.vector_db.table_exists():
            self.vector_db.create()
    
    def get_documents(self) -> List[DocumentResponse]:
        self.ensure_table_exists()
        document_info = self.vector_db.list_document_names()
        self.logger.info(f"Retrieved {len(document_info)} document infos from vector DB")

        # Group chunks by base document name
        document_groups = defaultdict(lambda: {'chunks': 0, 'pages': set(), 'content': []})
        for doc_info in document_info:
            name = doc_info['name']
            # Extract base name and page number
            match = re.match(r'(.+)_page_(\d+)', name)
            if match:
                base_name, page_num = match.groups()
                document_groups[base_name]['chunks'] += doc_info['chunks']
                document_groups[base_name]['pages'].add(int(page_num))
            else:
                # If it doesn't match the pattern, treat it as a single-chunk document
                document_groups[name]['chunks'] = doc_info['chunks']
            
            # Fetch the actual content
            content = self.vector_db.get_document_content(name)
            if content:
                document_groups[base_name if match else name]['content'].append(content)
            else:
                self.logger.warning(f"No content found for document: {name}")

        documents = []
        for base_name, info in document_groups.items():
            meta_data = {
                "total_chunks": info['chunks'],
                "total_pages": len(info['pages']) if info['pages'] else 1
            }
            combined_content = "\n\n".join(info['content'])
            documents.append(
                DocumentResponse(
                    id=base_name,
                    name=base_name,
                    content=combined_content,
                    meta_data=meta_data,
                    user_id=self.user.id,
                    org_id=self.user.organization_id,
                    created_at=None,
                    updated_at=None,
                    chunks=info['chunks']
                )
            )
            self.logger.info(f"Document: {base_name}, Chunks: {info['chunks']}, Content length: {len(combined_content)}")

        self.logger.info(f"Returning {len(documents)} documents")
        return documents
        
    def get_spaces(self) -> List[Dict[str, Any]]:
        try:
            spaces = self.confluence.get_all_spaces(start=0, limit=None)
            # Check if 'results' key exists in the response
            if isinstance(spaces, dict) and 'results' in spaces:
                return [{'key': space['key'], 'name': space['name']} for space in spaces['results']]
            elif isinstance(spaces, list):
                return [{'key': space['key'], 'name': space['name']} for space in spaces]
            else:
                raise ValueError(f"Unexpected response format from Confluence API: {spaces}")
        except Exception as e:
            self.logger.error(f"Error in get_spaces: {str(e)}", exc_info=True)
            return []  # Return an empty list in case of error

    def get_pages_in_space(self, space_key: str) -> List[Dict[str, Any]]:
        try:
            pages = self.confluence.get_all_pages_from_space(space_key, start=0, limit=None, status=None, expand='ancestors')
            return [self._format_page(page) for page in pages]
        except Exception as e:
            self.logger.error(f"Error in get_pages_in_space for space_key {space_key}: {str(e)}", exc_info=True)
            return []

    def _format_page(self, page: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'id': page['id'],
            'title': page['title'],
            'type': 'page',
            'parent_id': page['ancestors'][-1]['id'] if page['ancestors'] else None,
            'url': page['_links']['webui']
        }

    async def sync_selected_pages(self, space_key: str, page_ids: List[str]) -> Dict[str, Any]:
        synced_pages = []
        for page_id in page_ids:
            try:
                self.logger.info(f"Fetching page with ID: {page_id}")
                page = self.confluence.get_page_by_id(page_id, expand='body.storage')
                
                content = page.get('body', {}).get('storage', {}).get('value', '')
                
                if not content:
                    self.logger.warning(f"No content found for page {page_id}")
                    continue

                self.logger.info(f"Content found for page {page_id}. Length: {len(content)}")

                document = Document(
                    id=page['id'],
                    name=page['title'],
                    content=content,
                    meta_data={
                        "type": "confluence_page",
                        "space_key": space_key,
                        "url": page['_links']['webui'],
                        "user_id": self.user.id,
                        "org_id": self.user.organization_id
                    }
                )
                self.logger.info(f"Loading document into knowledge base: {page['title']} (ID: {page['id']})")
                self.knowledge_base.load_document(document)
                synced_pages.append(document)
                self.logger.info(f"Synced page: {page['title']} (ID: {page['id']})")
            except Exception as e:
                self.logger.error(f"Error syncing page {page_id}: {str(e)}", exc_info=True)
        
        self.logger.info(f"Synced {len(synced_pages)} pages")
        return {"pages_synced": len(synced_pages)}

def get_confluence_service(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ConfluenceService:
    return ConfluenceService(db, user)

confluence_service = Depends(get_confluence_service)