from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class MilestoneBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    sequence: int = Field(default=0)
    project_id: int
    is_active: bool = True

class MilestoneCreate(MilestoneBase):
    pass

class MilestoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    sequence: Optional[int] = None
    is_active: Optional[bool] = None

class MilestoneResponse(MilestoneBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: int

    class Config:
        from_attributes = True 