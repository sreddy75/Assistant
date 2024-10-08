from datetime import datetime, timedelta
from typing import Optional
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import jwt

from src.backend.db.session import get_db
from src.backend.models.models import User, AzureDevOpsConfig
from src.backend.core.config import settings

# Debug logging
import jwt
print(f"JWT library path: {jwt.__file__}")
print(f"JWT library version: {jwt.__version__}")

logger = logging.getLogger(__name__)

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    user = get_user(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = get_user(db, email=email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_user_with_devops_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Checking DevOps permissions for user: {current_user.id}, role: {current_user.role}, is_admin: {current_user.is_admin}")
    
    # Check if the user is a manager or an admin
    if current_user.role != "manager" and not current_user.is_admin:
        logger.warning(f"User {current_user.id} does not have sufficient permissions. Role: {current_user.role}, Is Admin: {current_user.is_admin}")
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    devops_config = db.query(AzureDevOpsConfig).filter(AzureDevOpsConfig.organization_id == current_user.organization_id).first()
    if not devops_config:
        logger.warning(f"Azure DevOps not configured for organization: {current_user.organization_id}")
        # Instead of raising an exception, we'll return the user with a flag indicating no DevOps config
        current_user.has_devops_config = False
        return current_user
    
    logger.info(f"User {current_user.id} has sufficient permissions for DevOps access")
    current_user.has_devops_config = True
    return current_user