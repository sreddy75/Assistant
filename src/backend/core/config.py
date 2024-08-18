from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "LLM Assistant API"
    PROJECT_VERSION: str = "1.0.0"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DB_URL: str 

    # Additional fields
    CLIENT_NAME: Optional[str] = None
    ENABLE_ENHANCED_QUALITY_ANALYST: bool = False
    ENABLE_ENHANCED_FINANCIAL_ANALYST: bool = False
    ENABLE_ENHANCED_DATA_ANALYST: bool = False
    ENABLE_WEB_SEARCH: bool = False
    ENABLE_PRODUCT_OWNER: bool = False
    ENABLE_BUSINESS_ANALYST: bool = False
    ENABLE_RESEARCH_ASSISTANT: bool = False
    ENABLE_CODE_ASSISTANT: bool = False
    ENABLE_COMPANY_ANALYST: bool = False
    ENABLE_FEEDBACK_SENTIMENT_ANALYSIS: bool = False
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_MODEL_NAME: Optional[str] = None
    EXA_API_KEY: Optional[str] = None
    PG_VECTOR_INSTANCE: Optional[str] = None
    DB_URL: Optional[str] = None
    GMAIL_USER: Optional[str] = None
    GMAIL_PASSWORD: Optional[str] = None
    OLLAMA_BASE_URL: Optional[str] = None
    BACKEND_URL: Optional[str] = None
    FRONTEND_URL: Optional[str] = None
    TOKENIZERS_PARALLELISM: Optional[bool] = None

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

