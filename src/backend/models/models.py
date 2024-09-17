# src/backend/models/models.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
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
    azure_devops_config = relationship("AzureDevOpsConfig", back_populates="organization", uselist=False)

class AzureDevOpsConfig(Base):
    __tablename__ = "azure_devops_configs"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), unique=True)
    organization_url = Column(String, nullable=False)
    personal_access_token = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="azure_devops_config")

class OrganizationConfig(Base):
    __tablename__ = "organization_configs"
    id = Column(Integer, primary_key=True, index=True)
    roles = Column(String)  # JSON string of roles
    assistants = Column(String)  # JSON string of assistant mappings
    feature_flags = Column(String)  # JSON string of feature flags
    instructions = Column(String)  # File path to instructions.json
    chat_system_icon = Column(String)  # File path to chat_system_icon.png
    chat_user_icon = Column(String)  # File path to chat_user_icon.png
    config_toml = Column(Text)  # TOML content as text
    main_image = Column(String)  # File path to main_image.png
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
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



class DevOpsProject(Base):
    __tablename__ = "devops_projects"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    project_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)

    organization = relationship("Organization")
    teams = relationship("DevOpsTeam", back_populates="project")
    dora_metrics = relationship("DORAMetric", back_populates="project")
    dora_snapshots = relationship("DORAMetricSnapshot", back_populates="project")

class WorkItemType(Base):
    __tablename__ = "work_item_types"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("devops_projects.id"))
    name = Column(String, nullable=False)
    fields = Column(JSON)

    project = relationship("DevOpsProject")

class DevOpsCache(Base):
    __tablename__ = "devops_cache"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    cache_key = Column(String, index=True)
    cache_value = Column(JSON)
    expires_at = Column(DateTime(timezone=True))

    organization = relationship("Organization")
    
class DORAMetric(Base):
    __tablename__ = "dora_metrics"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("devops_projects.id"))
    team_id = Column(Integer, ForeignKey("devops_teams.id"))
    metric_type = Column(String, index=True)  # 'deployment_frequency', 'lead_time', 'time_to_restore', 'change_failure_rate'
    metric_value = Column(Float)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("DevOpsProject", back_populates="dora_metrics")
    team = relationship("DevOpsTeam", back_populates="dora_metrics")

class DORAMetricSnapshot(Base):
    __tablename__ = "dora_metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("devops_projects.id"))
    team_id = Column(Integer, ForeignKey("devops_teams.id"))
    snapshot_data = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("DevOpsProject", back_populates="dora_snapshots")
    team = relationship("DevOpsTeam", back_populates="dora_snapshots")    

class DevOpsTeam(Base):
    __tablename__ = "devops_teams"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("devops_projects.id"))
    team_id = Column(String, nullable=False)
    name = Column(String, nullable=False)

    project = relationship("DevOpsProject", back_populates="teams")
    dora_metrics = relationship("DORAMetric", back_populates="team")
    dora_snapshots = relationship("DORAMetricSnapshot", back_populates="team")    