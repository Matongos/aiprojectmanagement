from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from .user import User

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    key: Optional[str] = None
    status: str = "active"
    privacy_level: str = "private"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    color: str = "#3498db"
    is_template: bool = False
    is_active: bool = True

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    progress: float = 0.0
    task_count: Optional[int] = 0

    class Config:
        from_attributes = True 