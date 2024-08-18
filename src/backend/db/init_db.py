from src.backend.models.models import Base, Organization, OrganizationConfig, User
from src.backend.core.config import settings
from src.backend.db.session import engine, SessionLocal
from passlib.context import CryptContext
import json
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def init_db():
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")
    
    db = SessionLocal()
    try:
        # Check if default organization exists
        default_org = db.query(Organization).filter(Organization.name == "KR8 IT PTY LTD").first()
        if not default_org:
            print("Creating default organization and super admin user...")
            # Create default organization config
            default_org_config = OrganizationConfig(
                roles=json.dumps(["Super Admin", "Admin", "User"]),
                assistants=json.dumps({"default_assistant": True}),
                feature_flags=json.dumps({"enable_feedback_sentiment_analysis": True})
            )
            db.add(default_org_config)
            db.flush()

            # Create default organization
            default_org = Organization(
                name="KR8 IT PTY LTD",
                config_id=default_org_config.id
            )
            db.add(default_org)
            db.flush()

            # Create super admin user
            super_admin = User(
                email="suren@kr8it.com",
                hashed_password=get_password_hash("Sur3n#12"),
                first_name="Super",
                last_name="Admin",
                nickname="SuperAdmin",
                role="Super Admin",
                is_active=True,
                is_admin=True,
                is_super_admin=True,
                trial_end=datetime.utcnow() + timedelta(days=365),
                email_verified=True,
                organization_id=default_org.id
            )
            db.add(super_admin)

            db.commit()
            print("Default organization and super admin user created.")
        else:
            print("Default organization already exists.")
    finally:
        db.close()

    print("Database initialization complete.")