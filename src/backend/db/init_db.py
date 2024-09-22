import toml
from src.backend.models.models import Base, Organization, OrganizationConfig, User
from src.backend.core.config import settings
from src.backend.db.session import engine, SessionLocal
from passlib.context import CryptContext
import json
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

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
            print("Creating default organization...")
            # Create default organization config
            default_org_config = OrganizationConfig(
                roles=json.dumps({
                    "Dev": ["Web Search", "Code Assistant"],
                    "QA": ["Web Search", "Enhanced Quality Analyst", "Business Analyst"],
                    "Product": ["Web Search", "Product Owner", "Business Analyst", "Enhanced Data Analyst"],
                    "Delivery": ["Web Search", "Business Analyst", "Enhanced Data Analyst"],
                    "Manager": ["Web Search", "Code Assistant", "Product Owner", "Enhanced Financial Analyst", "Business Analyst", "Enhanced Data Analyst"],
                    "Admin": ["Web Search", "Code Assistant", "Product Owner", "Enhanced Financial Analyst", "Business Analyst", "Enhanced Data Analyst"],
                    "Super Admin": ["Web Search", "Code Assistant", "Product Owner", "Business Analyst", "Project Management Assistant"]
                }),
                assistants=json.dumps({"default_assistant": True, "project_management_assistant": True}),
                feature_flags=json.dumps({"enable_feedback_sentiment_analysis": True}),
                config_toml=toml.dumps({
                    "theme": {
                        "primaryColor": "#0c5c2f",
                        "backgroundColor": "#134094",
                        "secondaryBackgroundColor": "#1d1e21",
                        "textColor": "#f5fafa",
                        "font": "sans serif"
                    }
                })
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
            print("Default organization created.")
        else:
            print("Default organization already exists.")

        # Check if super admin user exists
        super_admin = db.query(User).filter(User.email == "suren@kr8it.com").first()
        if not super_admin:
            print("Creating super admin user...")
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
            print("Super admin user created.")
        else:
            print("Super admin user already exists.")

        db.commit()
        print("Database initialization complete.")
    except IntegrityError as e:
        db.rollback()
        print(f"IntegrityError occurred: {str(e)}")
        print("This may be due to a race condition if multiple processes are trying to initialize the database simultaneously.")
        print("If this error persists, please check your database constraints and data.")
    except Exception as e:
        db.rollback()
        print(f"An unexpected error occurred: {str(e)}")
    finally:
        db.close()