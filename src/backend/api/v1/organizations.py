import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from requests import Session
from src.backend.schemas.organization import OrganizationCreate, OrganizationUpdate
from src.backend.models.models import Organization, OrganizationConfig, User
from src.backend.helpers.auth import get_current_user
from src.backend.core.client_config import get_db
from src.backend.utils.org_utils import load_org_config

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/")
async def create_organization(org: OrganizationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can create organizations")
    
    org_config = OrganizationConfig(
        roles=json.dumps(org.roles),
        assistants=json.dumps(org.assistants),
        feature_flags=json.dumps(org.feature_flags)
    )
    db.add(org_config)
    db.flush()

    new_org = Organization(name=org.name, config_id=org_config.id)
    db.add(new_org)
    db.commit()
    return {"message": f"Organization '{org.name}' created successfully"}

@router.put("/{org_id}")
async def update_organization(org_id: int, org_update: OrganizationUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can update organizations")
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    config = db.query(OrganizationConfig).filter(OrganizationConfig.id == org.config_id).first()
    if org_update.roles is not None:
        config.roles = json.dumps(org_update.roles)
    if org_update.assistants is not None:
        config.assistants = json.dumps(org_update.assistants)
    if org_update.feature_flags is not None:
        config.feature_flags = json.dumps(org_update.feature_flags)

    db.commit()
    return {"message": f"Organization updated successfully"}

@router.get("/")
async def list_organizations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can list organizations")
    
    orgs = db.query(Organization).all()
    return [{"id": org.id, "name": org.name} for org in orgs]

@router.get("/{org_id}")
async def get_organization(org_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can view organization details")
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    config = db.query(OrganizationConfig).filter(OrganizationConfig.id == org.config_id).first()
    return {
        "id": org.id,
        "name": org.name,
        "roles": json.loads(config.roles),
        "assistants": json.loads(config.assistants),
        "feature_flags": json.loads(config.feature_flags)
    }
    
@router.get("/org-config")
async def get_org_config(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    config = load_org_config(current_user.organization_id)
    return config

@router.get("/{org_name}/roles")
async def get_organization_roles(org_name: str, db: Session = Depends(get_db)):
    organization = db.query(Organization).filter(Organization.name == org_name).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org_config = load_org_config(organization.id)
    roles = org_config.get("roles", [])
    return {"roles": roles}
