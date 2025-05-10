from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from sqlalchemy import desc

from models.comment import Comment
from models.user import User
from schemas.comment import CommentCreate, CommentUpdate
from crud.base import CRUDBase


def get_comment(db: Session, comment_id: int) -> Optional[Comment]:
    """Get a comment by ID."""
    return db.query(Comment).filter(Comment.id == comment_id).first()


def get_comments_by_task(db: Session, task_id: int, skip: int = 0, limit: int = 100) -> List[Comment]:
    """Get all comments for a task."""
    return db.query(Comment)\
        .filter(Comment.task_id == task_id, Comment.parent_id.is_(None))\
        .order_by(desc(Comment.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()


def get_replies(db: Session, comment_id: int, skip: int = 0, limit: int = 100) -> List[Comment]:
    """Get all replies to a comment."""
    return db.query(Comment)\
        .filter(Comment.parent_id == comment_id)\
        .order_by(Comment.created_at)\
        .offset(skip)\
        .limit(limit)\
        .all()


def create_comment(db: Session, comment: CommentCreate, user_id: int) -> Comment:
    """Create a new comment."""
    db_comment = Comment(
        content=comment.content,
        task_id=comment.task_id,
        parent_id=comment.parent_id,
        created_by=user_id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


def update_comment(db: Session, comment_id: int, comment_update: CommentUpdate) -> Optional[Comment]:
    """Update a comment."""
    db_comment = get_comment(db, comment_id)
    if db_comment is None:
        return None
        
    update_data = comment_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_comment, key, value)
        
    db.commit()
    db.refresh(db_comment)
    return db_comment


def delete_comment(db: Session, comment_id: int) -> bool:
    """Delete a comment."""
    db_comment = get_comment(db, comment_id)
    if db_comment is None:
        return False
        
    db.delete(db_comment)
    db.commit()
    return True


def get_comment_with_user_data(db: Session, comment: Comment) -> Dict[str, Any]:
    """Enrich comment with user data."""
    user = db.query(User).filter(User.id == comment.created_by).first()
    
    if user:
        user_data = {
            "id": user.id,
            "name": user.full_name,
            "profile_image_url": user.profile_image_url
        }
    else:
        user_data = None
        
    return {
        "id": comment.id,
        "content": comment.content,
        "task_id": comment.task_id,
        "parent_id": comment.parent_id,
        "created_by": comment.created_by,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
        "user": user_data,
        "replies": []  # Will be populated separately if needed
    } 