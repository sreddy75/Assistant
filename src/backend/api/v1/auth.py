from datetime import UTC, datetime, timedelta
import json
import logging
import os
from src.backend.core.celery_app import celery_app
from email_validator import EmailNotValidError
from fastapi import APIRouter, Body, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
import jwt
from pydantic import EmailStr
from pydantic_core import ValidationError
from sqlalchemy.orm import Session
from src.backend.utils.org_utils import load_org_config
from src.backend.db.session import get_db
from src.backend.models.models import Organization, OrganizationConfig, User
from src.backend.schemas.user import Token, UserCreate, EmailSchema
from src.backend.helpers.auth import authenticate_user, create_access_token, get_password_hash, get_user
from src.backend.helpers.email import send_verification_email, send_password_reset_email
from src.backend.core.config import settings

router = APIRouter()

# Security setup
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.get("/validate_token")
async def validate_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"valid": True, "email": payload.get("sub")}
    except jwt.PyJWTError:
        return {"valid": False}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if not user.email_verified:
        raise HTTPException(status_code=401, detail="Email not verified")
    if user.trial_end.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=403, detail="Trial period has ended")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "org_id": user.organization_id},
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_super_admin": user.is_super_admin,
        "role": user.role,
        "org_id": user.organization_id,
        "trial_end": user.trial_end,
        "nickname": user.nickname,
        "organization": user.organization.name
    }

@celery_app.task(bind=True, max_retries=3)
def send_verification_email_task(self, email: str, token: str):
    try:
        send_verification_email(email, token)
    except Exception as exc:
        logger.error(f"Failed to send verification email to {email}: {exc}")
        raise self.retry(exc=exc, countdown=60)  # Retry after 1 minute

@router.post("/register")
async def register(user: UserCreate, org_name: str, db: Session = Depends(get_db)):
    db_user = get_user(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    organization = db.query(Organization).filter(Organization.name == org_name).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Fetch the organization config from the database
    org_config = db.query(OrganizationConfig).filter(OrganizationConfig.id == organization.config_id).first()
    if not org_config:
        raise HTTPException(status_code=404, detail="Organization configuration not found")
    
    # Parse the roles from the JSON string stored in the database
    available_roles = json.loads(org_config.roles)
    
    if user.role not in available_roles:
        raise HTTPException(status_code=400, detail="Invalid role for this organization")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email, 
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        nickname=user.nickname,
        role=user.role,
        organization_id=organization.id,
        trial_end=datetime.now(UTC) + timedelta(days=7),
        is_active=False,
        is_admin=False,
        is_super_admin=False,
        email_verified=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    verification_token = create_access_token(data={"sub": new_user.email})
    
    # Use Celery to send the verification email asynchronously with retries
    send_verification_email_task.delay(new_user.email, verification_token)
    
    logger.info(f"User registered successfully: {new_user.email}")
    return {"message": "User created successfully. Please check your email for verification."}

@router.get("/verify-email/{token}")
async def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = get_user(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.email_verified:
        return {"message": "Email already verified"}
    
    user.email_verified = True
    db.commit()
    return {"message": "Email verified successfully"}

@router.post("/request-password-reset")
async def request_password_reset(email_data: EmailSchema, db: Session = Depends(get_db)):
    user = get_user(db, email=email_data.email)
    if not user:
        return {"message": "If a user with that email exists, a password reset link has been sent."}
    
    reset_token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(hours=1))
    send_password_reset_email(user.email, reset_token)
    
    return {"message": "If a user with that email exists, a password reset link has been sent."}

@router.post("/reset-password")
async def reset_password(token: str = Body(...), new_password: str = Body(...), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = get_user(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return {"message": "Password reset successfully"}

@router.post("/logout")
async def logout():
    # In a stateless API, we don't need to do anything for logout
    # The client should discard the token
    return {"message": "Logged out successfully"}

@router.get("/is_authenticated")
async def is_authenticated(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return {"authenticated": False}
    except jwt.PyJWTError:
        return {"authenticated": False}
    return {"authenticated": True}

@router.get("/check_admin/{email}")
async def check_user_is_admin(email: str, db: Session = Depends(get_db)):
    user = get_user(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"is_admin": user.is_admin}