import logging
import math
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.backend.db.session import get_db
from src.backend.models.models import UserEvent
from src.backend.services.analytics_service import AnalyticsService

router = APIRouter()

analytics_service = AnalyticsService()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def replace_nan_with_none(obj):
    if isinstance(obj, float) and math.isnan(obj):
        return None
    elif isinstance(obj, dict):
        return {k: replace_nan_with_none(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_nan_with_none(v) for v in obj]
    return obj

@router.get("/sentiment-analysis")
async def get_sentiment_analysis(db: Session = Depends(get_db)):
    try:
        logger.debug("Entering get_sentiment_analysis endpoint")
        result = analytics_service.get_sentiment_analysis(db)
        logger.debug(f"Raw result from get_sentiment_analysis: {result}")
        cleaned_result = replace_nan_with_none(result)
        logger.debug(f"Cleaned result from get_sentiment_analysis: {cleaned_result}")
        return cleaned_result
    except Exception as e:
        logger.exception("Error in get_sentiment_analysis endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feedback-analysis")
async def get_feedback_analysis(db: Session = Depends(get_db)):
    try:
        logger.debug("Entering get_feedback_analysis endpoint")
        result = analytics_service.analyze_feedback_text(db)
        logger.debug(f"Raw result from analyze_feedback_text: {result}")
        cleaned_result = replace_nan_with_none(result)
        logger.debug(f"Cleaned result from analyze_feedback_text: {cleaned_result}")
        return cleaned_result
    except Exception as e:
        logger.exception("Error in get_feedback_analysis endpoint")
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/user-events")
async def save_user_event(event: UserEvent, db: Session = Depends(get_db)):
    try:
        logger.debug(f"Entering save_user_event endpoint with event: {event}")
        result = analytics_service.save_user_event(
            db, 
            event.user_id,             
            event.event_type, 
            event.event_data, 
            event.duration
        )
        logger.debug(f"Result from save_user_event: {result}")
        return {"message": "Event saved successfully"}
    except Exception as e:
        logger.exception("Error in save_user_event endpoint")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/user-events")
async def get_user_events(user_id: int = None, db: Session = Depends(get_db)):
    try:
        logger.debug(f"Entering get_user_events endpoint with user_id: {user_id}")
        result = analytics_service.get_user_events(db, user_id)
        logger.debug(f"Raw result from get_user_events: {result}")
        cleaned_result = replace_nan_with_none(result)
        logger.debug(f"Cleaned result from get_user_events: {cleaned_result}")
        return cleaned_result
    except Exception as e:
        logger.exception("Error in get_user_events endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/event-summary")
async def get_event_summary(db: Session = Depends(get_db)):
    try:
        logger.debug("Entering get_event_summary endpoint")
        result = analytics_service.get_event_summary(db)
        logger.debug(f"Raw result from get_event_summary: {result}")
        cleaned_result = replace_nan_with_none(result)
        logger.debug(f"Cleaned result from get_event_summary: {cleaned_result}")
        return cleaned_result
    except Exception as e:
        logger.exception("Error in get_event_summary endpoint")
        raise HTTPException(status_code=500, detail=str(e))