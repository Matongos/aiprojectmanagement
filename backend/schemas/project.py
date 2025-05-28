from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from .user import User
from .tag import Tag
from enum import Enum

class ProjectStage(str, Enum):
    TODO = "to_do"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"

class StageDefinition(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    key: Optional[str] = None
    status: str = "active"
    stage_id: Optional[int] = None
    privacy_level: str = "private"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    color: str = "#3498db"
    is_template: bool = False
    is_active: bool = True
    allow_milestones: bool = True
    tag_ids: Optional[List[int]] = Field(default=[], description="List of tag IDs")

class ProjectCreate(ProjectBase):
    """Schema for project creation"""
    pass

class ProjectUpdate(BaseModel):
    """Schema for project updates"""
    name: Optional[str] = None
    description: Optional[str] = None
    key: Optional[str] = None
    status: Optional[str] = None
    stage_id: Optional[int] = None
    privacy_level: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    color: Optional[str] = None
    is_template: Optional[bool] = None
    is_active: Optional[bool] = None
    allow_milestones: Optional[bool] = None
    tag_ids: Optional[List[int]] = None

class Project(ProjectBase):
    """Complete project schema with all fields"""
    id: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    progress: float = 0.0
    task_count: Optional[int] = 0
    member_count: Optional[int] = 0
    tags: Optional[List[Tag]] = Field(default=[], description="List of associated tags")

    class Config:
        from_attributes = True 