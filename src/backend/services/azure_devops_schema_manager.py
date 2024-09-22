import requests
import base64
from typing import List
from src.backend.kr8.document.base import Document
from src.backend.kr8.knowledge.azure_devops_knowledge import AzureDevOpsKnowledge
from src.backend.core.config import settings

class AzureDevOpsSchemaManager:
    def __init__(self, azure_devops_knowledge: AzureDevOpsKnowledge):
        self.azure_devops_knowledge = azure_devops_knowledge
        self.organization = settings.AZURE_DEVOPS_ORGANIZATION
        self.pat = settings.AZURE_DEVOPS_PERSONAL_ACCESS_TOKEN
        self.base_url = f"https://dev.azure.com/{self.organization}/_apis/distributedtask/swagger"

    def fetch_and_store_schema(self):
        credentials = f":{self.pat}"
        base64_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        headers = {
            'Authorization': f'Basic {base64_credentials}'
        }

        try:
            response = requests.get(self.base_url, headers=headers)
            response.raise_for_status()
            swagger_json = response.json()
            self.azure_devops_knowledge.fetch_and_store_endpoints(swagger_json)
            print("Successfully processed Swagger JSON")
        except Exception as e:
            print(f"Failed to process Swagger JSON: {str(e)}")

    def search_endpoints(self, query: str, limit: int = 5) -> List[Document]:
        return self.azure_devops_knowledge.search_endpoints(query, limit)

    def get_all_endpoints(self) -> List[Document]:
        return self.azure_devops_knowledge.get_all_endpoints()

    def get_endpoint_by_name(self, name: str) -> Document:
        return self.azure_devops_knowledge.get_endpoint_by_name(name)

    def delete_endpoint(self, name: str) -> bool:
        return self.azure_devops_knowledge.delete_endpoint(name)

    def clear_all_endpoints(self) -> bool:
        return self.azure_devops_knowledge.clear_all_endpoints()