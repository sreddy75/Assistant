import requests
from src.backend.core.config import settings

class QueryExecutor:
    def __init__(self):
        self.azure_devops_base_url = settings.AZURE_DEVOPS_ORGANIZATION_URL
        self.headers = {
            "Authorization": f"Basic {settings.AZURE_DEVOPS_PERSONAL_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

    def execute_query(self, interpretation: dict):
        results = []
        for endpoint in interpretation['endpoints']:
            url = f"{self.azure_devops_base_url}{endpoint['path']}"
            method = endpoint['method']
            params = endpoint.get('parameters', {})

            if method.lower() == 'get':
                response = requests.get(url, headers=self.headers, params=params)
            elif method.lower() == 'post':
                response = requests.post(url, headers=self.headers, json=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            results.append(response.json())

        return results