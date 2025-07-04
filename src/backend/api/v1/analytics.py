import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.backend.db.session import get_db
from src.backend.schemas.user import UserEvent
from src.backend.services.analytics_service import AnalyticsService
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

router = APIRouter()
analytics_service = AnalyticsService()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.get("/all-analytics")
@cache(expire=300)  # Cache for 5 minutes
async def get_all_analytics(db: Session = Depends(get_db)):
    try:
        return {
            "sentiment_analysis": analytics_service.get_sentiment_analysis(db),
            "feedback_analysis": analytics_service.analyze_feedback_text(db),
            "user_engagement": analytics_service.get_user_engagement_metrics(db),
            "interaction_metrics": analytics_service.get_interaction_metrics(db),
            "quality_metrics": analytics_service.get_quality_metrics(db),
            "usage_patterns": analytics_service.get_usage_patterns(db),
            "user_retention": analytics_service.get_user_retention(db),
            "user_segmentation": analytics_service.get_user_segmentation(db),
            "feature_usage": analytics_service.get_feature_usage(db),
            "conversion_funnel": analytics_service.get_conversion_funnel(db),
            "churn_rate": analytics_service.get_churn_rate(db)
        }
    except Exception as e:
        logger.error(f"Error in get_all_analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/sentiment-analysis")
@cache(expire=300)
async def get_sentiment_analysis(db: Session = Depends(get_db)):
    try:
        return analytics_service.get_sentiment_analysis(db)
    except Exception as e:
        logger.error(f"Error in get_sentiment_analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/feedback-analysis")
@cache(expire=300)
async def get_feedback_analysis(db: Session = Depends(get_db)):
    try:
        return analytics_service.analyze_feedback_text(db)
    except Exception as e:
        logger.error(f"Error in get_feedback_analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/user-engagement")
@cache(expire=300)
async def get_user_engagement_metrics(db: Session = Depends(get_db)):
    try:
        return analytics_service.get_user_engagement_metrics(db)
    except Exception as e:
        logger.error(f"Error in get_user_engagement_metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/interaction-metrics")
@cache(expire=300)
async def get_interaction_metrics(db: Session = Depends(get_db)):
    try:
        return analytics_service.get_interaction_metrics(db)
    except Exception as e:
        logger.error(f"Error in get_interaction_metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/quality-metrics")
@cache(expire=300)
async def get_quality_metrics(db: Session = Depends(get_db)):
    try:
        return analytics_service.get_quality_metrics(db)
    except Exception as e:
        logger.error(f"Error in get_quality_metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/usage-patterns")
@cache(expire=300)
async def get_usage_patterns(db: Session = Depends(get_db)):
    try:
        return analytics_service.get_usage_patterns(db)
    except Exception as e:
        logger.error(f"Error in get_usage_patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/user-events")
async def save_user_event(event: UserEvent, db: Session = Depends(get_db)):
    try:
        result = analytics_service.save_user_event(
            db, 
            event.user_id,             
            event.event_type, 
            event.event_data, 
            event.duration
        )
        if result:
            # Clear the cache when new data is added
            await FastAPICache.clear(namespace="analytics")
            return {"message": "Event saved successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save event")
    except Exception as e:
        logger.error(f"Error in save_user_event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save event: {str(e)}")

@router.get("/user-events")
@cache(expire=300)
async def get_user_events(user_id: int = None, db: Session = Depends(get_db)):
    try:
        return analytics_service.get_user_events(db, user_id)
    except Exception as e:
        logger.error(f"Error in get_user_events: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user events: {str(e)}")

@router.get("/event-summary")
@cache(expire=300)
async def get_event_summary(db: Session = Depends(get_db)):
    try:
        return analytics_service.get_event_summary(db)
    except Exception as e:
        logger.error(f"Error in get_event_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch event summary: {str(e)}")

@router.get("/user-retention")
@cache(expire=300)
async def get_user_retention(db: Session = Depends(get_db)):
    try:
        return analytics_service.get_user_retention(db)
    except Exception as e:
        logger.error(f"Error in get_user_retention: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user retention data: {str(e)}")

@router.get("/user-segmentation")
@cache(expire=300)
async def get_user_segmentation(db: Session = Depends(get_db)):
    try:
        return analytics_service.get_user_segmentation(db)
    except Exception as e:
        logger.error(f"Error in get_user_segmentation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user segmentation data: {str(e)}")

@router.get("/feature-usage")
@cache(expire=300)
async def get_feature_usage(db: Session = Depends(get_db)):
    try:
        return analytics_service.get_feature_usage(db)
    except Exception as e:
        logger.error(f"Error in get_feature_usage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch feature usage data: {str(e)}")

@router.get("/user-journey/{user_id}")
@cache(expire=300)
async def get_user_journey(user_id: int, db: Session = Depends(get_db)):
    try:
        return analytics_service.get_user_journey(db, user_id)
    except Exception as e:
        logger.error(f"Error in get_user_journey: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user journey data: {str(e)}")

@router.get("/conversion-funnel")
@cache(expire=300)
async def get_conversion_funnel(db: Session = Depends(get_db)):
    try:
        return analytics_service.get_conversion_funnel(db)
    except Exception as e:
        logger.error(f"Error in get_conversion_funnel: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversion funnel data: {str(e)}")

@router.get("/churn-rate")
@cache(expire=300)
async def get_churn_rate(db: Session = Depends(get_db)):
    try:
        return analytics_service.get_churn_rate(db)
    except Exception as e:
        logger.error(f"Error in get_churn_rate: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch churn rate data: {str(e)}")