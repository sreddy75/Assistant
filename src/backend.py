from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from email_validator import validate_email, EmailNotValidError
import os
import yagmail
import logging
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
load_dotenv()

# Database setup
SQLALCHEMY_DATABASE_URL = os.getenv("DB_URL", "postgresql+psycopg://ai:ai@pgvector:5432/ai")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security setup
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")  # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

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

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    trial_end = Column(DateTime)
    email_verified = Column(Boolean, default=False)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None

class UserInDB(BaseModel):
    email: str
    is_active: bool
    is_admin: bool
    trial_end: datetime
    email_verified: bool

class UserCreate(BaseModel):
    email: EmailStr
    password: str

# Helper functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    user = get_user(db, email=email)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
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
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = get_user(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

import yagmail

def send_email(to_email: str, subject: str, html_content: str):
    try:
        # Use GMAIL_USER and GMAIL_PASSWORD directly
        yag = yagmail.SMTP({GMAIL_USER: "Compare the Meerkat"}, GMAIL_PASSWORD)
        yag.send(
            to=to_email,
            subject=subject,
            contents=[html_content, 'This is the plain text version for non-HTML email clients.']
        )
        logger.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise

def send_verification_email(email: str, token: str):
    subject = "Verify your email for Compare the Meerkat"
    html_content = f"""
    <html>
        <body>
            <h2>Welcome to Compare the Meerkat!</h2>
            <p>Please click the link below to verify your email address:</p>
            <p><a href="{BACKEND_URL}/verify-email/{token}">Verify Your Email</a></p>
            <p>If the link doesn't work, copy and paste this URL into your browser:</p>
            <p>{BACKEND_URL}/verify-email/{token}</p>
            <p>Simples!</p>
        </body>
    </html>
    """
    send_email(email, subject, html_content)

def send_password_reset_email(email: str, token: str):
    subject = "Reset Your Compare the Meerkat Password"
    html_content = f"""
    <html>
        <body>
            <h2>Reset Your Compare the Meerkat Password</h2>
            <p>Click the link below to reset your password:</p>
            <p><a href="{FRONTEND_URL}?token={token}">Reset Password</a></p>
            <p>If the link doesn't work, copy and paste this URL into your browser:</p>
            <p>{FRONTEND_URL}?token={token}</p>
            <p>This link will expire in 1 hour.</p>
            <p>Simples!</p>
        </body>
    </html>
    """
    send_email(email, subject, html_content)

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
    if user.trial_end < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Trial period has ended",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserInDB)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/register")
async def register(user: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_user = get_user(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    try:
        valid = validate_email(user.email)
        email = valid.email
    except EmailNotValidError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=email, 
        hashed_password=hashed_password,
        trial_end=datetime.utcnow() + timedelta(days=7)
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
        raise HTTPException(status_code=400, detail="Invalid token")
    
    user = get_user(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.email_verified:
        return RedirectResponse(url=f"{FRONTEND_URL}/?message=Email already verified")
    
    user.email_verified = True
    db.commit()
    return RedirectResponse(url=f"{FRONTEND_URL}/?message=Email verified successfully")

from pydantic import BaseModel

class EmailSchema(BaseModel):
    email: str

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

@app.post("/extend-trial")
async def extend_trial(user_email: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can extend trials")
    
    user = get_user(db, email=user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.trial_end = datetime.utcnow() + timedelta(days=7)
    db.commit()
    return {"message": "Trial extended successfully"}

if __name__ == "__main__":
    import uvicorn
    Base.metadata.create_all(bind=engine)
    uvicorn.run(app, host="0.0.0.0", port=8000)