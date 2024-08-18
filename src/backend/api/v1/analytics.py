from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.backend.db.session import get_db
from src.backend.services.analytics_service import analytics_service

router = APIRouter()

@router.get("/sentiment-analysis")
async def get_sentiment_analysis():
    return analytics_service.get_sentiment_analysis()

@router.get("/feedback-analysis")
async def get_feedback_analysis():
    return analytics_service.analyze_feedback_text()

@router.get("/user-events")
async def get_user_events(user_id: int = None):
    return analytics_service.get_user_events(user_id)

@router.get("/event-summary")
async def get_event_summary():
    return analytics_service.get_event_summary()

