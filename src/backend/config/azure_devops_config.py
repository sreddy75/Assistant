from pydantic_settings import BaseSettings
from typing import Optional

class AzureDevOpsSettings(BaseSettings):
    organization_url: Optional[str] = None
    personal_access_token: Optional[str] = None

    class Config:
        env_prefix = "AZURE_DEVOPS_"

azure_devops_settings = AzureDevOpsSettings()

def is_azure_devops_configured() -> bool:
    return azure_devops_settings.organization_url is not None and azure_devops_settings.personal_access_token is not None