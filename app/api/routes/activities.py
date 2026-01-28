from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import Optional

from core.database import get_db
from api.deps import get_current_active_user
from models.models import User, UserActivity

router = APIRouter()


@router.get("/")
async def get_activities(
    skip: int = 0,
    limit: int = 50,
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Get user activities"""
    query = db.query(UserActivity)
    
    if user_id:
        query = query.filter(UserActivity.user_id == user_id)
    
    activities = query.order_by(UserActivity.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "activities": [
            {
                "id": activity.id,
                "user_id": activity.user_id,
                "action_type": activity.action_type,
                "description": activity.description,
                "ip_address": activity.ip_address,
                "created_at": activity.created_at.isoformat() if activity.created_at else None
            }
            for activity in activities
        ],
        "total": query.count(),
        "skip": skip,
        "limit": limit
    }


@router.get("/{activity_id}")
async def get_activity(
    activity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific activity"""
    activity = db.query(UserActivity).filter(UserActivity.id == activity_id).first()
    
    if not activity:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return {
        "success": True,
        "activity": {
            "id": activity.id,
            "user_id": activity.user_id,
            "action_type": activity.action_type,
            "description": activity.description,
            "ip_address": activity.ip_address,
            "created_at": activity.created_at.isoformat() if activity.created_at else None
        }
    }
