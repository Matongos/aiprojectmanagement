from typing import Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    key: str = Field(..., min_length=1, max_length=10)
    status: str = "active"
    privacy_level: str = "private"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    color: str = "#3498db"
    is_template: bool = False
    meta_data: Optional[Dict[str, Any]] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    key: Optional[str] = Field(None, min_length=1, max_length=10)
    status: Optional[str] = None
    privacy_level: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    color: Optional[str] = None
    is_template: Optional[bool] = None
    meta_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class ProjectInDBBase(ProjectBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True

class Project(ProjectInDBBase):
    pass

class ProjectInDB(ProjectInDBBase):
    pass 