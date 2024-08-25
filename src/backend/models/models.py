import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from sqlalchemy import JSON, Column, Float, Integer, LargeBinary, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    config_id = Column(Integer, ForeignKey("organization_configs.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    users = relationship("User", back_populates="organization")
    config = relationship("OrganizationConfig", back_populates="organization")

class OrganizationConfig(Base):
    __tablename__ = "organization_configs"
    id = Column(Integer, primary_key=True, index=True)
    roles = Column(String)  # JSON string of roles
    assistants = Column(String)  # JSON string of assistant mappings
    feature_flags = Column(String)  # JSON string of feature flags
    instructions = Column(String)  # File path to instructions.json
    chat_system_icon = Column(String)  # File path to chat_system_icon.png
    chat_user_icon = Column(String)  # File path to chat_user_icon.png
    config_toml = Column(String)  # File path to config.toml
    main_image = Column(String)  # File path to main_image.png
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    organization = relationship("Organization", back_populates="config")

class TokenData(BaseModel):
    email: str | None = None
    
class UserAnalytics(Base):
    __tablename__ = "user_analytics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_type = Column(String(50))
    event_data = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    duration = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="analytics")
        
class User(Base):
    __tablename__ = "users"    

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    nickname = Column(String)
    role = Column(String)
    is_active = Column(Boolean)
    is_admin = Column(Boolean)
    is_super_admin = Column(Boolean)
    trial_end = Column(DateTime(timezone=True))
    email_verified = Column(Boolean)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="users")
    votes = relationship("Vote", back_populates="user")
    analytics = relationship("UserAnalytics", back_populates="user")

class UserEvent(BaseModel):
    user_id: int    
    event_type: str
    event_data: dict
    duration: Optional[float] = None
            
class Vote(Base):
    __tablename__ = "votes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) 
    query = Column(Text)
    response = Column(Text)
    is_upvote = Column(Boolean)
    sentiment_score = Column(Float)
    usefulness_rating = Column(Integer)
    feedback_text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="votes")

User.votes = relationship("Vote", back_populates="user")