from typing import List, Dict, Any
from atlassian import Confluence
from src.backend.kr8.document import Document
from src.backend.kr8.vectordb.pgvector.pgvector2 import PgVector2

class ConfluenceIntegration:
    def __init__(self, url: str, username: str, api_token: str):
        self.confluence = Confluence(
            url=url,
            username=username,
            password=api_token,
            cloud=True  # Set to False if using Confluence Server
        )

    def get_space_content(self, space_key: str, parent_id: str = None) -> List[Dict[str, Any]]:
        try:
            if parent_id:
                content = self.confluence.get_page_child_by_type(parent_id, type='page', start=0, limit=None)
            else:
                content = self.confluence.get_all_pages_from_space(space_key, start=0, limit=None, status=None, expand='body.storage')
            return content
        except Exception as e:
            raise Exception(f"Error fetching content from Confluence space: {str(e)}")

    def get_page_content(self, page_id: str) -> str:
        try:
            content = self.confluence.get_page_by_id(page_id, expand='body.storage')
            return content['body']['storage']['value']
        except Exception as e:
            raise Exception(f"Error fetching page content from Confluence: {str(e)}")

    def recursively_get_pages(self, space_key: str, parent_id: str = None) -> List[Dict[str, Any]]:
        pages = self.get_space_content(space_key, parent_id)
        all_pages = []
        for page in pages:
            all_pages.append(page)
            child_pages = self.recursively_get_pages(space_key, page['id'])
            all_pages.extend(child_pages)
        return all_pages

    def store_documents_in_vector_db(self, space_key: str, vector_db: PgVector2) -> None:
        pages = self.recursively_get_pages(space_key)
        documents = []

        for page in pages:
            content = self.get_page_content(page['id'])
            doc = Document(
                id=page['id'],
                name=page['title'],
                content=content,
                meta_data={
                    "url": page['_links']['webui'],
                    "space_key": space_key,
                    "type": "confluence_page",
                    "parent_id": page.get('parentId')
                }
            )
            documents.append(doc)

        vector_db.upsert(documents)
        print(f"Stored {len(documents)} documents from Confluence space {space_key} in vector database.")

def setup_confluence_integration(confluence_url: str, username: str, api_token: str) -> ConfluenceIntegration:
    return ConfluenceIntegration(confluence_url, username, api_token)