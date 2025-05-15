from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TimeEntryBase(BaseModel):
    hours: float = Field(..., description="Number of hours spent", ge=0)
    description: Optional[str] = Field(None, description="Description of work done")
    task_id: int = Field(..., description="ID of the task this time entry belongs to")
    date: Optional[datetime] = Field(None, description="Date of the time entry")

class TimeEntryCreate(TimeEntryBase):
    pass

class TimeEntryUpdate(BaseModel):
    hours: Optional[float] = Field(None, description="Number of hours spent", ge=0)
    description: Optional[str] = Field(None, description="Description of work done")
    date: Optional[datetime] = Field(None, description="Date of the time entry")

class TimeEntryResponse(TimeEntryBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 