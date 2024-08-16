import os
from dotenv import load_dotenv
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from functools import lru_cache
import threading

# Import models
from backend.models import Organization, OrganizationConfig

# Load environment variables
load_dotenv()

# Database setup
SQLALCHEMY_DATABASE_URL = os.getenv("DB_URL", "postgresql+psycopg://ai:ai@pgvector:5432/ai")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Cache the configuration for 5 minutes to reduce database queries
@lru_cache(maxsize=1)
def get_cached_config(client_name):
    with get_db() as db:
        org = db.query(Organization).filter(Organization.name == client_name).first()
        if org:
            config = db.query(OrganizationConfig).filter(OrganizationConfig.id == org.config_id).first()
            if config:
                return {
                    "feature_flags": json.loads(config.feature_flags),
                    "roles": json.loads(config.roles),
                    "assistants": json.loads(config.assistants)
                }
    return None

def get_client_name():
    return os.getenv('CLIENT_NAME', 'default')

def get_config():
    client_name = get_client_name()
    config = get_cached_config(client_name)
    if config is None:
        # Fall back to default configuration
        with open('src/config/themes/default/feature_flags.json', 'r') as f:
            config = {
                "feature_flags": json.load(f),
                "roles": ["User"],
                "assistants": {}
            }
    return config

FEATURE_FLAGS = get_config()["feature_flags"]

def is_feedback_sentiment_analysis_enabled():
    return FEATURE_FLAGS.get("enable_feedback_sentiment_analysis", False)

def is_assistant_enabled(assistant_name):
    config = get_config()
    return config["assistants"].get(f"enable_{assistant_name.lower().replace(' ', '_')}", False)

# List of all available assistants
AVAILABLE_ASSISTANTS = [
    "Enhanced Data Analyst",
    "Enhanced Financial Analyst",
    "Product Owner",
    "Business Analyst",
    "Enhanced Quality Analyst",
    "Code Assistant",
    "Web Search",
    "Research Assistant",
    "Investment Assistant",
    "Company Analyst",
    "Maintenance Engineer",
]

# Get enabled assistants
def get_enabled_assistants():
    return [assistant for assistant in AVAILABLE_ASSISTANTS if is_assistant_enabled(assistant)]

ENABLED_ASSISTANTS = get_enabled_assistants()

def load_theme():
    client_name = get_client_name()
    theme_path = f"src/config/themes/{client_name}/config.toml"
    if not os.path.exists(theme_path):
        theme_path = "src/themes/default_config.toml"
    return theme_path

# Invalidate the cache every 5 minutes
def invalidate_config_cache():
    get_cached_config.cache_clear()

# Set up a background task to invalidate the cache every 5 minutes
def cache_invalidation_task():
    while True:
        invalidate_config_cache()
        threading.Timer(300, cache_invalidation_task).start()

# Start the cache invalidation task
cache_invalidation_task()