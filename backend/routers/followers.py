from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import get_current_user
from models.task import Task, task_followers
from models.user import User
from services.notification_service import NotificationService
from sqlalchemy import text

router = APIRouter(
    prefix="/projects/{project_id}/followers",
    tags=["followers"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)

notification_service = NotificationService()

@router.get("/", response_model=List[dict])
async def get_project_followers(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all followers for a project."""
    # Query to get followers with their details
    query = text("""
        SELECT u.id, u.username as name, u.email, u.profile_image_url
        FROM users u
        JOIN project_followers pf ON u.id = pf.user_id
        WHERE pf.project_id = :project_id
    """)
    
    followers = db.execute(query, {"project_id": project_id}).fetchall()
    return [dict(follower) for follower in followers]

@router.post("/{user_id}", status_code=status.HTTP_201_CREATED)
async def add_project_follower(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a follower to a project."""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already following
    query = text("""
        SELECT 1 FROM project_followers
        WHERE project_id = :project_id AND user_id = :user_id
    """)
    exists = db.execute(query, {"project_id": project_id, "user_id": user_id}).first()
    
    if exists:
        raise HTTPException(status_code=400, detail="User is already following this project")
    
    # Add follower
    query = text("""
        INSERT INTO project_followers (project_id, user_id)
        VALUES (:project_id, :user_id)
    """)
    db.execute(query, {"project_id": project_id, "user_id": user_id})
    db.commit()
    
    # Send notification to the new follower
    notification_data = {
        "user_id": user_id,
        "title": "Project Following",
        "content": f"You are now following project #{project_id}",
        "type": "project_follow",
        "reference_type": "project",
        "reference_id": project_id,
        "is_read": False
    }
    notification_service.create_notification(db, notification_data)
    
    return {"message": "Follower added successfully"}

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def remove_project_follower(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove a follower from a project."""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Remove follower
    query = text("""
        DELETE FROM project_followers
        WHERE project_id = :project_id AND user_id = :user_id
    """)
    result = db.execute(query, {"project_id": project_id, "user_id": user_id})
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="User is not following this project")
    
    return {"message": "Follower removed successfully"}

@router.get("/info", response_model=dict)
async def get_follower_info(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get follower info for a project (count and whether current user is following)."""
    # Get follower count
    count_query = text("""
        SELECT COUNT(*) as count
        FROM project_followers
        WHERE project_id = :project_id
    """)
    count_result = db.execute(count_query, {"project_id": project_id}).first()
    follower_count = count_result.count if count_result else 0
    
    # Check if current user is following
    is_following_query = text("""
        SELECT 1 FROM project_followers
        WHERE project_id = :project_id AND user_id = :user_id
    """)
    is_following = db.execute(
        is_following_query, 
        {"project_id": project_id, "user_id": current_user["id"]}
    ).first() is not None
    
    return {
        "follower_count": follower_count,
        "is_following": is_following
    } 