from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from crud import comment as crud
from crud import task as task_crud
from schemas.comment import Comment as CommentSchema, CommentCreate, CommentUpdate
from database import get_db
from routers.auth import get_current_user
from services.notification_service import NotificationService

router = APIRouter(
    prefix="/comments",
    tags=["comments"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)


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


@router.post("/", response_model=CommentSchema)
async def create_comment(
    comment: CommentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new comment."""
    # Create the comment
    db_comment = crud.create_comment(db, comment, current_user["id"])
    
    # Send notifications to relevant users if this is a task comment
    if comment.task_id:
        task = task_crud.get(db, comment.task_id)
        if task:
            # Get list of users involved with this task
            users_to_notify = set()
            if task.created_by:
                users_to_notify.add(task.created_by)
            if task.assignee_id:
                users_to_notify.add(task.assignee_id)
                
            # Send notifications
            if users_to_notify:
                NotificationService.notify_task_comment(
                    db=db,
                    task_id=task.id,
                    task_title=task.title,
                    comment_by_id=current_user["id"],
                    user_ids=list(users_to_notify)
                )
    
    return crud.get_comment_with_user_data(db, db_comment)


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
        
    updated_comment = crud.update_comment(db, comment_id, comment)
    return crud.get_comment_with_user_data(db, updated_comment)


@router.delete("/{comment_id}")
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
        
    success = crud.delete_comment(db, comment_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete comment")
        
    return {"message": "Comment deleted successfully"} 