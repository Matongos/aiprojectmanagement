from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TimeEntryBase(BaseModel):
    description: Optional[str] = None
    activity_type: Optional[str] = None
    is_billable: bool = True
    task_id: int
    project_id: int
    user_id: int

class TimeEntryCreate(TimeEntryBase):
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None

class TimeEntryUpdate(BaseModel):
    description: Optional[str] = None
    activity_type: Optional[str] = None
    is_billable: Optional[bool] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None

class TimeEntryInDB(TimeEntryBase):
    id: int
    start_time: datetime
    end_time: Optional[datetime]
    duration: float
    is_running: bool
    productivity_score: Optional[float]
    efficiency_metrics: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class TimeEntryWithRelations(TimeEntryInDB):
    task_name: str
    project_name: str
    user_name: str

class TimeEntryStats(BaseModel):
    total_hours: float
    billable_hours: float
    productivity_average: float
    entries_count: int
    activity_breakdown: dict
    daily_distribution: dict

class TimeEntryBulkCreate(BaseModel):
    entries: List[TimeEntryCreate]

class TimeEntryAIInsights(BaseModel):
    entry_id: int
    productivity_score: float
    efficiency_metrics: dict
    recommendations: List[str]
    patterns: dict 