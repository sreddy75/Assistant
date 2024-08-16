import datetime
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    config_id = Column(Integer, ForeignKey("organization_configs.id"))
    
    users = relationship("User", back_populates="organization")
    config = relationship("OrganizationConfig", back_populates="organization")

class OrganizationConfig(Base):
    __tablename__ = "organization_configs"
    id = Column(Integer, primary_key=True, index=True)
    roles = Column(String)  # JSON string of roles
    assistants = Column(String)  # JSON string of assistant mappings
    feature_flags = Column(String)  # JSON string of feature flags
    
    organization = relationship("Organization", back_populates="config")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    nickname = Column(String)
    role = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_super_admin = Column(Boolean, default=False)
    trial_end = Column(DateTime)
    email_verified = Column(Boolean, default=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    
    organization = relationship("Organization", back_populates="users")
    
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
    
    user = relationship("User", back_populates="votes")

User.votes = relationship("Vote", back_populates="user")
    