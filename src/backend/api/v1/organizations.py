from asyncio.log import logger
import json
import os
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from src.backend.utils.org_utils import load_org_config
from src.backend.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationWithFiles, OrganizationResponse
from src.backend.models.models import Organization, OrganizationConfig, User
from src.backend.helpers.auth import get_current_user
from src.backend.core.client_config import get_db
from src.backend.core.config import UPLOAD_DIR

router = APIRouter()

@router.get("/public-asset/{org_name}/{asset_type}")
async def get_public_organization_asset(org_name: str, asset_type: str, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.name == org_name).first()
    if not org:
        logger.error(f"Organization not found: {org_name}")
        raise HTTPException(status_code=404, detail="Organization not found")
    
    config = db.query(OrganizationConfig).filter(OrganizationConfig.id == org.config_id).first()
    
    asset_path = getattr(config, asset_type, None)
    logger.info(f"Attempting to retrieve asset: {asset_type}, path: {asset_path}")
    if not asset_path or not os.path.exists(asset_path):
        logger.error(f"Asset not found: {asset_type}, path: {asset_path}")
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return FileResponse(asset_path)

@router.get("/public-config/{org_name}")
async def get_public_organization_config(org_name: str, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.name == org_name).first()
    if not org:
        logger.error(f"Organization not found: {org_name}")
        raise HTTPException(status_code=404, detail="Organization not found")
    
    config = db.query(OrganizationConfig).filter(OrganizationConfig.id == org.config_id).first()
    
    if not config.config_toml or not os.path.exists(config.config_toml):
        logger.error(f"Config file not found for org: {org_name}")
        raise HTTPException(status_code=404, detail="Config file not found")
    
    return FileResponse(config.config_toml)

@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    org_data: OrganizationWithFiles = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can create organizations")
    
    org_config = OrganizationConfig(
        roles=json.dumps(org_data.roles),
        assistants=json.dumps(org_data.assistants),
        feature_flags=json.dumps(org_data.feature_flags),
        instructions=await save_file(org_data.instructions, f"instructions_{org_data.name}.json") if org_data.instructions else None,
        chat_system_icon=await save_file(org_data.chat_system_icon, f"chat_system_icon_{org_data.name}.png") if org_data.chat_system_icon else None,
        chat_user_icon=await save_file(org_data.chat_user_icon, f"chat_user_icon_{org_data.name}.png") if org_data.chat_user_icon else None,
        config_toml=await save_file(org_data.config_toml, f"config_{org_data.name}.toml") if org_data.config_toml else None,
        main_image=await save_file(org_data.main_image, f"main_image_{org_data.name}.png") if org_data.main_image else None
    )
    db.add(org_config)
    db.flush()

    new_org = Organization(name=org_data.name, config_id=org_config.id)
    db.add(new_org)
    db.commit()
    db.refresh(new_org)
    db.refresh(org_config)

    return OrganizationResponse(
        id=new_org.id,
        name=new_org.name,
        roles=json.loads(org_config.roles),
        assistants=json.loads(org_config.assistants),
        feature_flags=json.loads(org_config.feature_flags),
        config_id=org_config.id,
        instructions_path=org_config.instructions,
        chat_system_icon_path=org_config.chat_system_icon,
        chat_user_icon_path=org_config.chat_user_icon,
        config_toml_path=org_config.config_toml,
        main_image_path=org_config.main_image
    )

@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: int,
    name: Optional[str] = Form(None),
    roles: Optional[str] = Form(None),
    instructions: Optional[UploadFile] = File(None),
    chat_system_icon: Optional[UploadFile] = File(None),
    chat_user_icon: Optional[UploadFile] = File(None),
    config_toml: Optional[UploadFile] = File(None),
    main_image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can update organizations")
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    config = db.query(OrganizationConfig).filter(OrganizationConfig.id == org.config_id).first()
    
    if name:
        org.name = name
    if roles:
        config.roles = json.dumps([role.strip() for role in roles.split(',') if role.strip()])
    
    if instructions:
        config.instructions = await save_file(instructions, f"instructions_{org_id}.json")
    if chat_system_icon:
        config.chat_system_icon = await save_file(chat_system_icon, f"chat_system_icon_{org_id}.png")
    if chat_user_icon:
        config.chat_user_icon = await save_file(chat_user_icon, f"chat_user_icon_{org_id}.png")
    if config_toml:
        config.config_toml = await save_file(config_toml, f"config_{org_id}.toml")
    if main_image:
        config.main_image = await save_file(main_image, f"main_image_{org_id}.png")

    db.commit()
    db.refresh(org)
    db.refresh(config)

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        roles=json.loads(config.roles),
        assistants=json.loads(config.assistants),
        feature_flags=json.loads(config.feature_flags),
        config_id=config.id,
        instructions_path=config.instructions,
        chat_system_icon_path=config.chat_system_icon,
        chat_user_icon_path=config.chat_user_icon,
        config_toml_path=config.config_toml,
        main_image_path=config.main_image
    )

async def save_file(file: UploadFile, filename: str) -> str:
    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        return file_path
    except Exception as e:
        logger.error(f"Error saving file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

@router.get("/asset/{org_name}/login-form/main_image")
async def get_organization_main_image(org_name: str, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.name == org_name).first()
    if not org:
        logger.error(f"Organization not found: {org_name}")
        raise HTTPException(status_code=404, detail="Organization not found")
    
    config = db.query(OrganizationConfig).filter(OrganizationConfig.id == org.config_id).first()
    
    main_image_path = config.main_image
    logger.info(f"Attempting to retrieve main image for org: {org_name}, path: {main_image_path}")
    if not main_image_path or not os.path.exists(main_image_path):
        logger.error(f"Main image not found for org: {org_name}, path: {main_image_path}")
        raise HTTPException(status_code=404, detail="Main image not found")
    
    return FileResponse(main_image_path)
        
@router.get("/asset/{org_id}/{asset_type}")
async def get_organization_asset(org_id: int, asset_type: str, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        logger.error(f"Organization not found: {org_id}")
        raise HTTPException(status_code=404, detail="Organization not found")
    
    config = db.query(OrganizationConfig).filter(OrganizationConfig.id == org.config_id).first()
    
    asset_path = getattr(config, asset_type, None)
    logger.info(f"Attempting to retrieve asset: {asset_type}, path: {asset_path}")
    if not asset_path or not os.path.exists(asset_path):
        logger.error(f"Asset not found: {asset_type}, path: {asset_path}")
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return FileResponse(asset_path)

async def save_file(file: UploadFile, filename: str) -> str:
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    return file_path

@router.get("/")
async def list_organizations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can list organizations")
    
    orgs = db.query(Organization).join(OrganizationConfig).all()
    return [{"id": org.id, "name": org.name, "roles": json.loads(org.config.roles) if org.config.roles else []} for org in orgs]

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
