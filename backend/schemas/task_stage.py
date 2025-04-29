from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from .task import Task

class TaskStageBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    sequence_order: int = 0

class TaskStageCreate(TaskStageBase):
    project_id: int

class TaskStageUpdate(TaskStageBase):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sequence_order: Optional[int] = None

class TaskStageInDB(TaskStageBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaskStage(TaskStageInDB):
    tasks: Optional[List[Task]] = None 