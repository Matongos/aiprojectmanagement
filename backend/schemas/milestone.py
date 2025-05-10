from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, Field

class MilestoneBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_id: int
    due_date: Optional[date] = None
    completed_date: Optional[date] = None
    is_completed: bool = False
    is_active: bool = True

class MilestoneCreate(MilestoneBase):
    pass

class MilestoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[date] = None
    completed_date: Optional[date] = None
    is_completed: Optional[bool] = None
    is_active: Optional[bool] = None

class MilestoneResponse(MilestoneBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None

    class Config:
        from_attributes = True 