from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from crud import comment as crud
from crud import task as task_crud
from schemas.comment import Comment as CommentSchema, CommentCreate, CommentUpdate
from database import get_db
from routers.auth import get_current_user
from services.notification_service import NotificationService
from models.user import User
from services import comment_service, user_service
from models.task import Task
from models.activity import Activity
from models.comment import Comment

router = APIRouter(
    prefix="/comments",
    tags=["comments"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)

notification_service = NotificationService()

@router.get("/task/{task_id}", response_model=List[CommentSchema])
async def read_task_comments(
    task_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all comments for a specific task."""
    comments = crud.get_comments_by_task(db, task_id, skip=skip, limit=limit)
    
    # Enrich with user data and get replies
    result = []
    for comment in comments:
        comment_data = crud.get_comment_with_user_data(db, comment)
        replies = crud.get_replies(db, comment.id)
        comment_data["replies"] = [crud.get_comment_with_user_data(db, reply) for reply in replies]
        result.append(comment_data)
        
    return result


@router.get("/{comment_id}/replies", response_model=List[CommentSchema])
async def read_comment_replies(
    comment_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all replies to a specific comment."""
    replies = crud.get_replies(db, comment_id, skip=skip, limit=limit)
    return [crud.get_comment_with_user_data(db, reply) for reply in replies]


@router.post("/", response_model=CommentSchema, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment: CommentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new comment."""
    try:
        # Get task details
        task = db.query(Task).filter(Task.id == comment.task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Create the comment first
        db_comment = Comment(
            content=comment.content,
            task_id=comment.task_id,
            parent_id=comment.parent_id,
            created_by=current_user["id"]
        )
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        
        # Process mentions in comment content
        if comment.content:
            user_service.process_user_mentions(
                db, 
                comment.content, 
                current_user["id"], 
                "comment", 
                db_comment.id,
                notification_service
            )
        
        # Send notification to task owner (if different from commenter)
        if task.created_by != current_user["id"]:
            notification_data = {
                "user_id": task.created_by,
                "title": "New Comment on Task",
                "content": f"New comment on task: {task.name}",
                "type": "comment",
                "reference_type": "comment",
                "reference_id": db_comment.id,
                "is_read": False
            }
            notification_service.create_notification(db, notification_data)
        
        # Notify task assignee if different from commenter and creator
        if task.assigned_to and task.assigned_to != current_user["id"] and task.assigned_to != task.created_by:
            notification_data = {
                "user_id": task.assigned_to,
                "title": "New Comment on Task",
                "content": f"New comment on task: {task.name}",
                "type": "comment",
                "reference_type": "comment",
                "reference_id": db_comment.id,
                "is_read": False
            }
            notification_service.create_notification(db, notification_data)
        
        return crud.get_comment_with_user_data(db, db_comment)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{comment_id}", response_model=CommentSchema)
async def update_comment(
    comment_id: int,
    comment: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a comment."""
    db_comment = crud.get_comment(db, comment_id)
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
        
    # Check if user is the comment author
    if db_comment.user_id != current_user["id"] and not current_user["is_superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized to update this comment")
        
    updated_comment, error = crud.update_comment(db, comment_id, comment)
    
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    
    # Process mentions in updated comment content
    if comment.content:
        user_service.process_user_mentions(
            db, 
            comment.content, 
            current_user["id"], 
            "comment", 
            comment_id,
            notification_service
        )
    
    return crud.get_comment_with_user_data(db, updated_comment)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a comment."""
    db_comment = crud.get_comment(db, comment_id)
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
        
    # Check if user is the comment author
    if db_comment.user_id != current_user["id"] and not current_user["is_superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
        
    error = crud.delete_comment(db, comment_id)
    
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
        
    return {"message": "Comment deleted successfully"}


@router.get("/latest", response_model=List[CommentSchema])
async def read_latest_comments(
    skip: int = 0,
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get latest comments across all tasks."""
    query = text("""
        SELECT 
            c.id, c.content, c.task_id, c.parent_id, c.created_by,
            c.created_at, c.updated_at,
            u.id as user_id, u.username, u.full_name, u.profile_image_url,
            t.name as task_name,
            p.id as project_id, p.name as project_name
        FROM comments c
        JOIN users u ON c.created_by = u.id
        JOIN tasks t ON c.task_id = t.id
        JOIN projects p ON t.project_id = p.id
        WHERE c.parent_id IS NULL
        ORDER BY c.created_at DESC
        LIMIT :limit OFFSET :skip
    """)
    
    results = db.execute(query, {"limit": limit, "skip": skip}).fetchall()
    
    comments = []
    for row in results:
        comments.append({
            "id": row.id,
            "content": row.content,
            "task_id": row.task_id,
            "parent_id": row.parent_id,
            "created_by": row.created_by,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "user": {
                "id": row.user_id,
                "username": row.username,
                "full_name": row.full_name,
                "profile_image_url": row.profile_image_url
            },
            "task": {
                "id": row.task_id,
                "name": row.task_name
            },
            "project": {
                "id": row.project_id,
                "name": row.project_name
            }
        })
    
    return comments 