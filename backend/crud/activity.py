from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, and_

from models.activity import Activity
from models.user import User
from schemas.activity import ActivityCreate, ActivityUpdate


def get_activity(db: Session, activity_id: int) -> Optional[Activity]:
    """Get an activity by ID."""
    return db.query(Activity).filter(Activity.id == activity_id).first()


def get_activities_by_task(db: Session, task_id: int, skip: int = 0, limit: int = 100) -> List[Activity]:
    """Get all activities for a task."""
    return db.query(Activity)\
        .filter(Activity.task_id == task_id)\
        .order_by(desc(Activity.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()


def get_activities_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Activity]:
    """Get all activities for a user."""
    return db.query(Activity)\
        .filter(Activity.user_id == user_id)\
        .order_by(desc(Activity.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()


def get_activities_by_project(db: Session, project_id: int, skip: int = 0, limit: int = 100) -> List[Activity]:
    """Get all activities for a project."""
    return db.query(Activity)\
        .filter(Activity.project_id == project_id)\
        .order_by(desc(Activity.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()


def create_activity(db: Session, activity: ActivityCreate) -> Activity:
    """Create a new activity."""
    db_activity = Activity(
        activity_type=activity.activity_type,
        description=activity.description,
        task_id=activity.task_id,
        project_id=activity.project_id,
        user_id=activity.user_id
    )
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    return db_activity


def update_activity(db: Session, activity_id: int, activity_update: ActivityUpdate) -> Optional[Activity]:
    """Update an activity."""
    db_activity = get_activity(db, activity_id)
    if db_activity is None:
        return None
        
    update_data = activity_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_activity, key, value)
        
    db.commit()
    db.refresh(db_activity)
    return db_activity


def delete_activity(db: Session, activity_id: int) -> bool:
    """Delete an activity."""
    db_activity = get_activity(db, activity_id)
    if db_activity is None:
        return False
        
    db.delete(db_activity)
    db.commit()
    return True


def get_activity_with_user_data(db: Session, activity: Activity) -> Dict[str, Any]:
    """Enrich activity with user data."""
    user = db.query(User).filter(User.id == activity.user_id).first()
    
    if user:
        user_data = {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "profile_image_url": user.profile_image_url
        }
    else:
        user_data = None
        
    return {
        "id": activity.id,
        "activity_type": activity.activity_type,
        "description": activity.description,
        "task_id": activity.task_id,
        "project_id": activity.project_id,
        "user_id": activity.user_id,
        "created_at": activity.created_at,
        "user": user_data
    } 