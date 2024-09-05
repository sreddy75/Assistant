import os
from dotenv import load_dotenv
import json
from sqlalchemy.orm import Session
from src.backend.models.models import Organization, OrganizationConfig
from src.backend.db.session import get_db
from contextlib import contextmanager

load_dotenv()

def get_client_name():
    return os.getenv('CLIENT_NAME', 'default')

def load_theme():    
    client_name = get_client_name()    
    theme_path = f"src/backend/config/themes/{client_name}/config.toml"
    if not os.path.exists(theme_path):
        theme_path = "src/backend/config/themes/default_config.toml"
    return theme_path

@contextmanager
def get_db_context():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

def get_cached_config(client_name):
    with get_db_context() as db:
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

def get_config():
    client_name = get_client_name()
    config = get_cached_config(client_name)
    if config is None:
        # Fall back to default configuration
        default_org = get_cached_config("Default Organization")
        if default_org:
            return default_org
        else:
            return {
                "feature_flags": {"enable_feedback_sentiment_analysis": False},
                "roles": ["User"],
                "assistants": {}
            }
    return config

FEATURE_FLAGS = get_config()["feature_flags"]

def is_feedback_sentiment_analysis_enabled():
    return FEATURE_FLAGS.get("enable_feedback_sentiment_analysis", False)

def is_assistant_enabled(assistant_name):
    return FEATURE_FLAGS.get(f"enable_{assistant_name.lower().replace(' ', '_')}", False)

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
    "Call Center Assistant",
]

ENABLED_ASSISTANTS = [assistant for assistant in AVAILABLE_ASSISTANTS if is_assistant_enabled(assistant)]