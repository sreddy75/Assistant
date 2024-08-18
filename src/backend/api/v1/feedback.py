from fastapi import APIRouter, Depends
from requests import Session
from textblob import TextBlob

from src.backend.helpers.auth import get_current_user
from src.backend.models.models import User, Vote
from src.backend.core.client_config import FEATURE_FLAGS, get_db


router = APIRouter()

def is_feedback_sentiment_analysis_enabled():
    return FEATURE_FLAGS.get("enable_feedback_sentiment_analysis", False)


@router.post("/submit-feedback")
async def submit_feedback(
    feedback_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if is_feedback_sentiment_analysis_enabled():
        # Perform sentiment analysis on the feedback text
        sentiment = TextBlob(feedback_data["feedback_text"]).sentiment.polarity

        new_vote = Vote(
            user_id=current_user.id,
            query=feedback_data["query"],
            response=feedback_data["response"],
            is_upvote=feedback_data["is_upvote"],
            sentiment_score=sentiment,
            usefulness_rating=feedback_data["usefulness_rating"],
            feedback_text=feedback_data["feedback_text"]
        )
    else:
        new_vote = Vote(
            user_id=current_user.id,
            query=feedback_data["query"],
            response=feedback_data["response"],
            is_upvote=feedback_data["is_upvote"]
        )
    
    db.add(new_vote)
    db.commit()
    return {"message": "Feedback submitted successfully"}

@router.post("/submit-vote")
async def submit_vote(
    vote_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_vote = Vote(
        user_id=current_user.id,
        query=vote_data["query"],
        response=vote_data["response"],
        is_upvote=vote_data["is_upvote"]
    )
    db.add(new_vote)
    db.commit()
    return {"message": "Vote submitted successfully"}
