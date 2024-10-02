import logging
from fastapi import FastAPI
from src.backend.db.init_db import init_db
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Starting main.py execution")

# Initialize the database first
logger.debug("About to call init_db()")
init_db()
logger.debug("init_db() completed")

# Now import the rest of your modules
from src.backend.core.config import settings
from src.backend.api.v1 import (auth, users, organizations, feedback, 
                                knowledge_base, assistant, chat, analytics,
                                project_management, agile_team)

logger.debug(f"DATABASE_URL: {settings.DB_URL}")

app = FastAPI()

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(organizations.router, prefix="/api/v1/organizations", tags=["organizations"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])
app.include_router(knowledge_base.router, prefix="/api/v1/knowledge-base", tags=["knowledge-base"]) 
app.include_router(assistant.router, prefix="/api/v1/assistant", tags=["assistant"]) 
app.include_router(agile_team.router, prefix="/api/v1/agile-team", tags=["agile-team"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"]) 
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"]) 
app.include_router(project_management.router, prefix="/api/v1/project-management", tags=["Project Management"])

@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend())
    
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.backend.main:app", host="0.0.0.0", port=8000, reload=True)