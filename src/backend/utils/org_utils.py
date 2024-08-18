import json
from sqlalchemy.orm import Session
from src.backend.models.models import Organization, OrganizationConfig
from src.backend.db.session import get_db

def load_org_config(org_id: int):
    db = next(get_db())
    try:
        org_config = db.query(OrganizationConfig).join(Organization).filter(Organization.id == org_id).first()
        if not org_config:
            raise ValueError(f"No configuration found for organization {org_id}")
        
        config = {
            "roles": json.loads(org_config.roles),
            "assistants": json.loads(org_config.assistants),
            "feature_flags": json.loads(org_config.feature_flags)
        }
        return config
    finally:
        db.close()