from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class CommentBase(BaseModel):
    content: str = Field(..., min_length=1)
    task_id: int
    parent_id: Optional[int] = None
    mentions: Optional[List[int]] = None  # List of user IDs mentioned

class CommentCreate(CommentBase):
    pass

class CommentUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)

class CommentInDB(CommentBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Comment(CommentInDB):
    user: Optional[Dict[str, Any]] = None  # User info (simplified)
    replies: Optional[List['Comment']] = None  # Recursive for nested comments

Comment.model_rebuild()  # This handles the recursive reference 