from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from models.project import ProjectStatus

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.PLANNING
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[int] = None
    priority: int = Field(default=1, ge=1, le=5)
    tags: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[ProjectStatus] = None
    is_active: Optional[bool] = None

class ProjectInDB(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

class Project(ProjectInDB):
    pass 