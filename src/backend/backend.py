 #Standard library imports
import os
import sys
import json
import logging
from datetime import datetime, timedelta, UTC
from typing import List
from contextlib import asynccontextmanager

# Third-party imports
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from email_validator import validate_email, EmailNotValidError
from textblob import TextBlob
import yagmail
from dotenv import load_dotenv

# Local imports
from config.client_config import FEATURE_FLAGS, get_db
from backend.models import Base, User, Organization, OrganizationConfig, Vote
from backend.schemas.user_schema import EmailSchema, Token, UserCreate, UserInDB, UserResponse
from backend.schemas.organization_schema import OrganizationCreate, OrganizationUpdate
from backend.helpers.auth_helper import authenticate_user, create_access_token, get_current_user, get_password_hash, get_user
from backend.helpers.email_helper import send_password_reset_email, send_verification_email

load_dotenv()

# Database setup
SQLALCHEMY_DATABASE_URL = os.getenv("DB_URL", "postgresql+psycopg://ai:ai@pgvector:5432/ai")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Security setup
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")  # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
    
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_db()

# Environment variables
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")

if not GMAIL_USER or not GMAIL_PASSWORD:
    raise ValueError("GMAIL_USER and GMAIL_PASSWORD must be set as environment variables")

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_feedback_sentiment_analysis_enabled():
    return FEATURE_FLAGS.get("enable_feedback_sentiment_analysis", False)

def load_org_config(db: Session, org_id: int):
    org_config = db.query(OrganizationConfig).join(Organization).filter(Organization.id == org_id).first()
    if not org_config:
        raise ValueError(f"No configuration found for organization {org_id}")
    
    config = {
        "roles": json.loads(org_config.roles),
        "assistants": json.loads(org_config.assistants),
        "feature_flags": json.loads(org_config.feature_flags)
    }
    return config


# Routes
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )    
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified",
        )
    if user.trial_end.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trial period has ended",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "org_id": user.organization_id},
        expires_delta=access_token_expires
    )
    
    org = db.query(Organization).filter(Organization.id ==  user.organization_id).first()
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_id": user.id,
        "role": user.role, 
        "nickname": user.nickname,
        "organization": org.name,
    }



@app.post("/organizations")
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

@app.put("/organizations/{org_id}")
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

@app.get("/organizations")
async def list_organizations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can list organizations")
    
    orgs = db.query(Organization).all()
    return [{"id": org.id, "name": org.name} for org in orgs]

@app.get("/organizations/{org_id}")
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
    
@app.get("/org-config")
async def get_org_config(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    config = load_org_config(db, current_user.organization_id)
    return config

@app.get("/users", response_model=List[UserResponse])
async def get_all_users(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    users = db.query(User).all()
    return users

@app.get("/users/me", response_model=UserInDB)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/organizations/{org_name}/roles")
async def get_organization_roles(org_name: str, db: Session = Depends(get_db)):
    organization = db.query(Organization).filter(Organization.name == org_name).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org_config = load_org_config(db, organization.id)
    roles = org_config.get("roles", [])
    return {"roles": roles}

@app.post("/register")
async def register(user: UserCreate, org_name: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_user = get_user(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    organization = db.query(Organization).filter(Organization.name == org_name).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org_config = load_org_config(db, organization.id)
    available_roles = org_config.get("roles", [])
    
    if user.role not in available_roles:
        raise HTTPException(status_code=400, detail="Invalid role for this organization")
    
    try:
        valid = validate_email(user.email)
        email = valid.email
    except EmailNotValidError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=email, 
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        nickname=user.nickname,
        role=user.role,
        organization_id=organization.id,
        trial_end=datetime.now(UTC) + timedelta(days=7)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    verification_token = create_access_token(data={"sub": new_user.email})
    background_tasks.add_task(send_verification_email, new_user.email, verification_token)
    
    return {"message": "User created successfully. Please check your email for verification."}

@app.get("/verify-email/{token}")
async def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = get_user(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.email_verified:
        return {"message": "Email already verified"}
    
    user.email_verified = True
    db.commit()
    return {"message": "Email verified successfully"}

@app.post("/request-password-reset")
async def request_password_reset(email_data: EmailSchema, db: Session = Depends(get_db)):
    email = email_data.email
    user = get_user(db, email=email)
    if not user:
        # Don't reveal if the user exists or not for security reasons
        return {"message": "If a user with that email exists, a password reset link has been sent."}
    
    reset_token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(hours=1))
    send_password_reset_email(user.email, reset_token)
    
    return {"message": "If a user with that email exists, a password reset link has been sent."}

@app.post("/reset-password")
async def reset_password(token: str = Body(...), new_password: str = Body(...), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.error("Invalid token: email not found in payload")
            raise HTTPException(status_code=400, detail="Invalid token")
    except JWTError as e:
        logger.error(f"JWT Error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = get_user(db, email=email)
    if not user:
        logger.error(f"User not found for email: {email}")
        raise HTTPException(status_code=404, detail="User not found")
    
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    logger.info(f"Password reset successfully for user: {email}")
    
    return {"message": "Password reset successfully"}

@app.get("/users/{email}/is-admin")
async def check_user_is_admin(email: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    user = get_user(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"is_admin": user.is_admin}

@app.post("/extend-trial/{user_id}")
async def extend_trial(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can extend trials"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.trial_end = datetime.now(UTC) + timedelta(days=7)
    db.commit()
    return {"message": "Trial extended successfully"}

@app.post("/submit-feedback")
async def submit_feedback(
    feedback_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if is_feedback_sentiment_analysis_enabled():
        # Perform sentiment analysis on the feedback text
        sentiment = TextBlob(feedback_data["feedback_text"]).sentiment.polarity

        new_vote = Vote(
            user_id=current_user.id,
            query=feedback_data["query"],
            response=feedback_data["response"],
            is_upvote=feedback_data["is_upvote"],
            sentiment_score=sentiment,
            usefulness_rating=feedback_data["usefulness_rating"],
            feedback_text=feedback_data["feedback_text"]
        )
    else:
        new_vote = Vote(
            user_id=current_user.id,
            query=feedback_data["query"],
            response=feedback_data["response"],
            is_upvote=feedback_data["is_upvote"]
        )
    
    db.add(new_vote)
    db.commit()
    return {"message": "Feedback submitted successfully"}

@app.post("/submit-vote")
async def submit_vote(
    vote_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_vote = Vote(
        user_id=current_user.id,
        query=vote_data["query"],
        response=vote_data["response"],
        is_upvote=vote_data["is_upvote"]
    )
    db.add(new_vote)
    db.commit()
    return {"message": "Vote submitted successfully"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."}
    )

def init_db():
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    db = SessionLocal()
    try:
        # Check if super admin user exists, if not create one
        super_admin_user = db.query(User).filter(User.is_super_admin == True).first()
        if not super_admin_user:
            # Create default organization
            default_org_config = OrganizationConfig(
                roles=json.dumps(["Super Admin", "Admin", "User"]),
                assistants=json.dumps({"default_assistant": True}),
                feature_flags=json.dumps({"enable_feedback_sentiment_analysis": True})
            )
            db.add(default_org_config)
            db.flush()

            default_org = Organization(
                name="Default Organization",
                config_id=default_org_config.id
            )
            db.add(default_org)
            db.flush()

            hashed_password = get_password_hash("superadmin123")  # Change this password!
            super_admin_user = User(
                email="superadmin@example.com",  # Change this email!
                hashed_password=hashed_password,
                first_name="Super",
                last_name="Admin",
                nickname="SuperAdmin",
                role="Super Admin",
                is_active=True,
                is_admin=True,
                is_super_admin=True,
                trial_end=datetime.now(UTC) + timedelta(days=365),  # Set a long trial period for super admin
                email_verified=True,
                organization_id=default_org.id
            )
            db.add(super_admin_user)
            db.commit()
            logger.info("Super Admin user and Default Organization created.")
        else:
            logger.info("Super Admin user already exists.")

        # Check if regular admin user exists, if not create one
        admin_user = db.query(User).filter(User.is_admin == True, User.is_super_admin == False).first()
        if not admin_user:
            hashed_password = get_password_hash("adminpassword")  # Change this password!
            admin_user = User(
                email="admin@example.com",  # Change this email!
                hashed_password=hashed_password,
                first_name="Admin",
                last_name="User",
                nickname="Admin",
                role="Admin",
                is_active=True,
                is_admin=True,
                is_super_admin=False,
                trial_end=datetime.now(UTC) + timedelta(days=30),
                email_verified=True,
                organization_id=db.query(Organization).filter(Organization.name == "Default Organization").first().id
            )
            db.add(admin_user)
            db.commit()
            logger.info("Regular Admin user created.")
        else:
            logger.info("Regular Admin user already exists.")

    except Exception as e:
        logger.error(f"Error during database initialization: {str(e)}")
        db.rollback()
    finally:
        db.close()
    logger.info("Database initialization complete.")
        
if __name__ == "__main__":
    import uvicorn
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)