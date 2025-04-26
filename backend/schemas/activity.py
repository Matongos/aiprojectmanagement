from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ActivityBase(BaseModel):
    """Base model for activity schema."""
    activity_type: str
    description: str
    project_id: int
    task_id: Optional[int] = None
    user_id: int

class ActivityCreate(ActivityBase):
    """Schema for creating a new activity."""
    pass

class ActivityUpdate(BaseModel):
    """Schema for updating an activity."""
    activity_type: Optional[str] = None
    description: Optional[str] = None

class ActivityInDB(ActivityBase):
    """Schema for activity data in the database."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class Activity(ActivityInDB):
    """Schema for activity data returned to the client."""
    user: Optional[Dict[str, Any]] = None 