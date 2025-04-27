from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from crud import comment as crud
from crud import task as task_crud
from schemas.comment import Comment as CommentSchema, CommentCreate, CommentUpdate
from database import get_db
from routers.auth import get_current_user
from services.notification_service import NotificationService
from models.user import User
from services import comment_service, user_service

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
    current_user: User = Depends(get_current_user)
):
    """Create a new comment."""
    created_comment, error = comment_service.create_comment(db, comment.dict(), current_user.id)
    
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    
    # Process mentions in comment content
    if comment.content:
        user_service.process_user_mentions(
            db, 
            comment.content, 
            current_user.id, 
            "comment", 
            created_comment["id"],
            notification_service
        )
    
    # Send notification to task owner (if different from commenter)
    task = comment_service.get_related_task(db, comment.task_id)
    if task and task.get("created_by") != current_user.id:
        notification_data = {
            "user_id": task["created_by"],
            "title": "New Comment on Task",
            "content": f"New comment on task: {task['title']}",
            "type": "comment",
            "reference_type": "comment",
            "reference_id": created_comment["id"],
            "is_read": False
        }
        notification_service.create_notification(db, notification_data)
    
    # Send notification to task assignee (if different from commenter and task owner)
    if task and task.get("assigned_to") and task["assigned_to"] != current_user.id and task["assigned_to"] != task.get("created_by"):
        notification_data = {
            "user_id": task["assigned_to"],
            "title": "New Comment on Task",
            "content": f"New comment on task: {task['title']}",
            "type": "comment",
            "reference_type": "comment",
            "reference_id": created_comment["id"],
            "is_read": False
        }
        notification_service.create_notification(db, notification_data)
    
    return created_comment


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