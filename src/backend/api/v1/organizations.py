from asyncio.log import logger
import json
import os
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
from src.backend.schemas.project_management import AzureDevOpsConfigUpdate
from src.backend.utils.org_utils import load_org_config
from src.backend.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationWithFiles, OrganizationResponse
from src.backend.models.models import Organization, OrganizationConfig, User, AzureDevOpsConfig
from src.backend.helpers.auth import get_current_user
from src.backend.core.client_config import get_db
from src.backend.core.config import UPLOAD_DIR
import toml

router = APIRouter()

async def save_file(file: UploadFile, filename: str) -> str:
    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        content = await file.read()
        if filename.endswith('.toml'):
            # Parse TOML content and store as string
            toml_dict = toml.loads(content.decode('utf-8'))
            with open(file_path, "w") as buffer:
                toml.dump(toml_dict, buffer)
        else:
            with open(file_path, "wb") as buffer:
                buffer.write(content)
        return file_path
    except Exception as e:
        logger.error(f"Error saving file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

@router.get("/public-asset/{org_name}/{asset_type}")
async def get_public_organization_asset(org_name: str, asset_type: str, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.name == org_name).first()
    if not org:
        logger.error(f"Organization not found: {org_name}")
        raise HTTPException(status_code=404, detail="Organization not found")
    
    config = db.query(OrganizationConfig).filter(OrganizationConfig.id == org.config_id).first()
    
    if asset_type == "config_toml":
        if not config.config_toml:
            logger.error(f"Config TOML not found for org: {org_name}")
            raise HTTPException(status_code=404, detail="Config TOML not found")
        return PlainTextResponse(content=config.config_toml, media_type="application/toml")
    
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
    
    if not config.config_toml:
        logger.error(f"Config TOML not found for org: {org_name}")
        raise HTTPException(status_code=404, detail="Config TOML not found")
    
    return PlainTextResponse(content=config.config_toml, media_type="application/toml")

@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    org_data: OrganizationWithFiles = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can create organizations")
    
    feature_flags_content = {}
    if org_data.feature_flags:
        feature_flags_content = json.loads(await org_data.feature_flags.read())

    roles_content = {}
    if org_data.roles:
        roles_content = json.loads(await org_data.roles.read())

    config_toml_content = ""
    if org_data.config_toml:
        config_toml_content = (await org_data.config_toml.read()).decode('utf-8')

    org_config = OrganizationConfig(
        roles=json.dumps(roles_content),
        assistants=json.dumps(org_data.assistants),
        feature_flags=json.dumps(feature_flags_content),
        config_toml=config_toml_content,
        instructions=await save_file(org_data.instructions, f"instructions_{org_data.name}.json") if org_data.instructions else None,
        chat_system_icon=await save_file(org_data.chat_system_icon, f"chat_system_icon_{org_data.name}.png") if org_data.chat_system_icon else None,
        chat_user_icon=await save_file(org_data.chat_user_icon, f"chat_user_icon_{org_data.name}.png") if org_data.chat_user_icon else None,
        main_image=await save_file(org_data.main_image, f"main_image_{org_data.name}.png") if org_data.main_image else None
    )
    db.add(org_config)
    db.flush()

    # Handle Azure DevOps configuration
    azure_devops_config = json.loads(org_data.azure_devops_config)
    azure_devops = AzureDevOpsConfig(
        url=azure_devops_config['url'],
        token=azure_devops_config['token'],
        project=azure_devops_config['project']
    )
    db.add(azure_devops)
    db.flush()

    new_org = Organization(name=org_data.name, config_id=org_config.id, azure_devops_config_id=azure_devops.id)
    db.add(new_org)
    db.commit()
    db.refresh(new_org)
    db.refresh(org_config)
    db.refresh(azure_devops)

    return OrganizationResponse(
        id=new_org.id,
        name=new_org.name,
        roles=roles_content,
        assistants=json.loads(org_config.assistants),
        feature_flags=feature_flags_content,
        config_id=org_config.id,
        instructions_path=org_config.instructions,
        chat_system_icon_path=org_config.chat_system_icon,
        chat_user_icon_path=org_config.chat_user_icon,
        config_toml=config_toml_content,
        main_image_path=org_config.main_image,
        azure_devops_url=azure_devops.url,
        azure_devops_project=azure_devops.project
    )

@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: int,
    name: Optional[str] = Form(None),
    instructions: Optional[UploadFile] = File(None),
    chat_system_icon: Optional[UploadFile] = File(None),
    chat_user_icon: Optional[UploadFile] = File(None),
    config_toml: Optional[UploadFile] = File(None),
    main_image: Optional[UploadFile] = File(None),
    feature_flags: Optional[str] = Form(None),
    roles: Optional[str] = Form(None),
    assistants: Optional[str] = Form(None),
    azure_devops_config: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can update organizations")
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    config = db.query(OrganizationConfig).filter(OrganizationConfig.id == org.config_id).first()
    
    # Handle Azure DevOps configuration
    azure_devops = db.query(AzureDevOpsConfig).filter(AzureDevOpsConfig.organization_id == org.id).first()

    if name:
        org.name = name
    
    # Handle file uploads (instructions, icons, main_image)
    for file_field in [instructions, chat_system_icon, chat_user_icon, main_image]:
        if file_field:
            file_content = await file_field.read()
            file_path = os.path.join(UPLOAD_DIR, f"{org.name}_{file_field.filename}")
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
            setattr(config, file_field.filename.split('.')[0], file_path)
    
    # Handle config_toml update
    if config_toml:
        config_toml_content = await config_toml.read()
        try:
            # Validate TOML content
            toml.loads(config_toml_content.decode('utf-8'))
            config.config_toml = config_toml_content.decode('utf-8')
        except toml.TomlDecodeError as e:
            logger.error(f"TOML decode error in config_toml: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid TOML in config_toml: {str(e)}")
    
    # Handle JSON data (feature_flags, roles, assistants)
    if feature_flags:
        try:
            json_content = json.loads(feature_flags)
            config.feature_flags = json.dumps(json_content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in feature flags: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON in feature flags: {str(e)}")

    if roles:
        try:
            roles_list = json.loads(roles)
            if not isinstance(roles_list, list) or not all(isinstance(role, str) for role in roles_list):
                raise ValueError("Roles must be a list of strings")
            config.roles = json.dumps(roles_list)
            logger.info(f"Updated roles: {roles_list}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in roles: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON in roles: {str(e)}")
        except ValueError as e:
            logger.error(f"Invalid roles structure: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid roles structure: {str(e)}")

    if assistants:
        try:
            json_content = json.loads(assistants)
            if not isinstance(json_content, dict):
                raise ValueError("Assistants must be a dictionary")
            for role, assistant_list in json_content.items():
                if not isinstance(assistant_list, list):
                    raise ValueError(f"Assistants for role '{role}' must be a list")
            config.assistants = json.dumps(json_content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in assistants: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON in assistants: {str(e)}")
        except ValueError as e:
            logger.error(f"Invalid assistants structure: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid assistants structure: {str(e)}")

    # Handle Azure DevOps configuration update
    if azure_devops_config:
        azure_devops_data = json.loads(azure_devops_config)
        if azure_devops is None:
            # Only create a new AzureDevOpsConfig if we have valid data
            if azure_devops_data.get('organization_url') and azure_devops_data.get('personal_access_token'):
                azure_devops = AzureDevOpsConfig(
                    organization_id=org.id,
                    organization_url=azure_devops_data['organization_url'],
                    personal_access_token=azure_devops_data['personal_access_token']                    
                )
                db.add(azure_devops)
                db.flush()
                org.azure_devops_config_id = azure_devops.id
        else:
            # Update existing AzureDevOpsConfig
            if azure_devops_data.get('organization_url'):
                azure_devops.organization_url = azure_devops_data['organization_url']
            if azure_devops_data.get('personal_access_token'):
                azure_devops.personal_access_token = azure_devops_data['personal_access_token']
            if azure_devops_data.get('project'):
                azure_devops.project = azure_devops_data['project']

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating organization in database")

    db.refresh(org)
    db.refresh(config)
    if azure_devops:
        db.refresh(azure_devops)

    # Process roles
    roles_data = json.loads(config.roles) if config.roles else {}
    roles_list = list(roles_data.keys()) if isinstance(roles_data, dict) else (roles_data if isinstance(roles_data, list) else [])

    # Process assistants
    assistants_data = json.loads(config.assistants) if config.assistants else {}
    if isinstance(assistants_data, dict) and 'default_assistant' in assistants_data:
        if isinstance(assistants_data['default_assistant'], bool):
            assistants_data['default_assistant'] = ['default_assistant'] if assistants_data['default_assistant'] else []

    # Process feature flags
    feature_flags_data = json.loads(config.feature_flags) if config.feature_flags else {}

    logger.debug(f"Roles data: {roles_data}")
    logger.debug(f"Assistants data: {assistants_data}")
    logger.debug(f"Feature flags data: {feature_flags_data}")
    
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        roles=json.loads(config.roles) if config.roles else [],
        assistants=json.loads(config.assistants) if config.assistants else {},
        feature_flags=json.loads(config.feature_flags) if config.feature_flags else {},
        config_id=config.id,
        instructions_path=config.instructions,
        chat_system_icon_path=config.chat_system_icon,
        chat_user_icon_path=config.chat_user_icon,
        config_toml=config.config_toml,
        main_image_path=config.main_image,
        azure_devops_url=azure_devops.organization_url if azure_devops else None,
        azure_devops_integrated=bool(azure_devops),
        azure_devops_org_url=azure_devops.organization_url if azure_devops else None
    )
        
@router.get("/asset/{org_id}/{asset_type}")
async def get_organization_asset(org_id: int, asset_type: str, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    config = db.query(OrganizationConfig).filter(OrganizationConfig.id == org.config_id).first()
    
    if asset_type in ["assistants", "roles", "feature_flags"]:
        data = getattr(config, asset_type)
        return json.loads(data) if data else {}
    elif asset_type == "config_toml":
        return PlainTextResponse(content=config.config_toml, media_type="application/toml")
    
    asset_path = getattr(config, asset_type, None)
    if not asset_path:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return FileResponse(asset_path)

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
    azure_devops = db.query(AzureDevOpsConfig).filter(AzureDevOpsConfig.id == org.azure_devops_config_id).first()
    
    return {
        "id": org.id,
        "name": org.name,
        "roles": json.loads(config.roles) if config.roles else [],
        "assistants": json.loads(config.assistants) if config.assistants else {},
        "feature_flags": json.loads(config.feature_flags) if config.feature_flags else {},
        "config_toml": json.loads(config.config_toml) if config.config_toml else {},
        "azure_devops_url": azure_devops.url if azure_devops else None,
        "azure_devops_project": azure_devops.project if azure_devops else None
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

@router.delete("/{org_id}")
async def delete_organization(org_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can delete organizations")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Delete associated configs
    db.query(OrganizationConfig).filter(OrganizationConfig.id == org.config_id).delete()
    db.query(AzureDevOpsConfig).filter(AzureDevOpsConfig.id == org.azure_devops_config_id).delete()

    # Delete the organization
    db.delete(org)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting organization: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting organization")

    return {"message": "Organization deleted successfully"}

@router.get("/azure-devops-config/{org_id}")
async def get_azure_devops_config(org_id: int, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    azure_devops = db.query(AzureDevOpsConfig).filter(AzureDevOpsConfig.organization_id == org.id).first()
    if not azure_devops:
        return {"organization_url": "", "personal_access_token": ""}

    return {"organization_url": azure_devops.organization_url, "personal_access_token": azure_devops.personal_access_token}


router.put("/azure-devops-config/{org_id}")
async def update_azure_devops_config(org_id: int, config: AzureDevOpsConfigUpdate, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    azure_devops = db.query(AzureDevOpsConfig).filter(AzureDevOpsConfig.organization_id == org.id).first()
    if not azure_devops:
        azure_devops = AzureDevOpsConfig(organization_id=org.id)
        db.add(azure_devops)

    azure_devops.organization_url = config.organization_url
    if config.personal_access_token:
        azure_devops.personal_access_token = config.personal_access_token
    azure_devops.project = config.project

    db.commit()
    return {"message": "Azure DevOps configuration updated successfully"}