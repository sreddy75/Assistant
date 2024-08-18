

# Logging setup
from datetime import UTC, datetime, timedelta
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from requests import Session

from src.backend.helpers.auth import get_current_user, get_user
from src.backend.models.models import User
from src.backend.schemas.user import UserInDB, UserResponse
from src.backend.core.client_config import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/users/me", response_model=UserInDB)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    users = db.query(User).all()
    return users

@router.get("/users/{email}/is-admin")
async def check_user_is_admin(email: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    user = get_user(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"is_admin": user.is_admin}

@router.post("/extend-trial/{user_id}")
async def extend_trial(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can extend trials"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.trial_end = datetime.now(UTC) + timedelta(days=7)
    db.commit()
    return {"message": "Trial extended successfully"}
