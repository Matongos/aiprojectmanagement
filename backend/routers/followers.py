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
    prefix="/{project_id}/followers",
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
    try:
        # Query to get followers with their details
        query = text("""
            SELECT u.id, u.username as name, u.email, u.profile_image_url
            FROM users u
            JOIN project_followers pf ON u.id = pf.user_id
            WHERE pf.project_id = :project_id
        """)
        
        result = db.execute(query, {"project_id": project_id})
        followers = []
        for row in result:
            followers.append({
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "profile_image_url": row.profile_image_url
            })
        return followers
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching followers: {str(e)}"
        )

@router.post("/{user_id}", status_code=status.HTTP_201_CREATED)
async def add_project_follower(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a follower to a project."""
    try:
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
        
        return {"message": "Follower added successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error adding follower: {str(e)}"
        )

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def remove_project_follower(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove a follower from a project."""
    try:
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if the user is a superuser
        is_superuser = user.is_superuser
        
        # Remove follower
        query = text("""
            DELETE FROM project_followers
            WHERE project_id = :project_id AND user_id = :user_id
        """)
        result = db.execute(query, {"project_id": project_id, "user_id": user_id})
        db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="User is not following this project")
        
        # If it was a superuser, send them a notification
        if is_superuser:
            notification_data = {
                "user_id": user_id,
                "title": "Project Following Removed",
                "content": f"You have been removed as a follower from project #{project_id}",
                "notification_type": "project_unfollow",
                "reference_type": "project",
                "reference_id": project_id,
                "is_read": False
            }
            notification_service.create_notification(db, notification_data)
        
        return {"message": "Follower removed successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error removing follower: {str(e)}"
        )

@router.get("/info")
async def get_follower_info(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get follower information including count and current user's following status."""
    try:
        # Get follower count
        count_query = text("""
            SELECT COUNT(*) as count
            FROM project_followers
            WHERE project_id = :project_id
        """)
        follower_count = db.execute(count_query, {"project_id": project_id}).scalar()

        # Check if current user is following
        following_query = text("""
            SELECT 1
            FROM project_followers
            WHERE project_id = :project_id AND user_id = :user_id
        """)
        is_following = bool(db.execute(
            following_query, 
            {"project_id": project_id, "user_id": current_user["id"]}
        ).first())

        return {
            "follower_count": follower_count,
            "is_following": is_following
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting follower info: {str(e)}"
        )

# Task followers endpoints
@router.get("/tasks/{task_id}", response_model=List[dict])
async def get_task_followers(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all followers for a task."""
    # Query to get followers with their details
    query = text("""
        SELECT u.id, u.username as name, u.email, u.profile_image_url
        FROM users u
        JOIN task_followers tf ON u.id = tf.user_id
        WHERE tf.task_id = :task_id
    """)
    
    followers = db.execute(query, {"task_id": task_id}).fetchall()
    return [dict(follower) for follower in followers]

@router.post("/tasks/{task_id}/{user_id}", status_code=status.HTTP_201_CREATED)
async def add_task_follower(
    task_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a follower to a task."""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already following
    query = text("""
        SELECT 1 FROM task_followers
        WHERE task_id = :task_id AND user_id = :user_id
    """)
    exists = db.execute(query, {"task_id": task_id, "user_id": user_id}).first()
    
    if exists:
        raise HTTPException(status_code=400, detail="User is already following this task")
    
    # Add follower
    query = text("""
        INSERT INTO task_followers (task_id, user_id)
        VALUES (:task_id, :user_id)
    """)
    db.execute(query, {"task_id": task_id, "user_id": user_id})
    db.commit()
    
    # Send notification to the new follower
    notification_data = {
        "user_id": user_id,
        "title": "Task Following",
        "content": f"You are now following task #{task_id}",
        "notification_type": "task_follow",
        "reference_type": "task",
        "reference_id": task_id,
        "is_read": False
    }
    notification_service.create_notification(db, notification_data)
    
    return {"message": "Follower added successfully"}

@router.delete("/tasks/{task_id}/{user_id}", status_code=status.HTTP_200_OK)
async def remove_task_follower(
    task_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove a follower from a task."""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Remove follower
    query = text("""
        DELETE FROM task_followers
        WHERE task_id = :task_id AND user_id = :user_id
    """)
    result = db.execute(query, {"task_id": task_id, "user_id": user_id})
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="User is not following this task")
    
    return {"message": "Follower removed successfully"} 