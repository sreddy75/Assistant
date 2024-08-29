import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# List of enabled assistants
ENABLED_ASSISTANTS = ["General Assistant", "Code Assistant", "Data Analyst"]

# Client name
CLIENT_NAME = os.getenv("CLIENT_NAME", "default_client")

# Application settings
APP_NAME = os.getenv("APP_NAME", "AI Assistant Platform")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# Debug mode
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "app.log")

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "mydatabase")
DB_USER = os.getenv("DB_USER", "myuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mypassword")

# Redis configuration (if used)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# JWT settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_DELTA = int(os.getenv("JWT_EXPIRATION_DELTA", "86400"))  # 24 hours in seconds

# File upload settings
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx'}
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "16777216"))  # 16MB

# API rate limiting
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))  # Number of requests
RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "3600"))  # Per hour

# Cache settings
CACHE_TYPE = os.getenv("CACHE_TYPE", "simple")
CACHE_REDIS_URL = os.getenv("CACHE_REDIS_URL", "redis://localhost:6379/0")
CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "300"))  # 5 minutes

# Email configuration (if needed)
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1", "t")
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "your-email@gmail.com")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "your-email-password")
MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "your-email@gmail.com")

# Third-party API keys (if needed)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your-anthropic-api-key")

# Feature flags
ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS", "True").lower() in ("true", "1", "t")
ENABLE_USER_FEEDBACK = os.getenv("ENABLE_USER_FEEDBACK", "True").lower() in ("true", "1", "t")
ENABLE_CHAT_HISTORY = os.getenv("ENABLE_CHAT_HISTORY", "True").lower() in ("true", "1", "t")

def get_client_name():
    return CLIENT_NAME

def get_db_url():
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_redis_url():
    return f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Add any other configuration-related functions here