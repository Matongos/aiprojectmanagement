from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from models.task import TaskStatus, TaskPriority

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    estimated_hours: Optional[int] = None
    actual_hours: Optional[int] = None
    tags: Optional[str] = None

class TaskCreate(TaskBase):
    project_id: int
    assignee_id: Optional[int] = None

class TaskUpdate(TaskBase):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee_id: Optional[int] = None

class TaskInDB(TaskBase):
    id: int
    project_id: int
    creator_id: int
    assignee_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Task(TaskInDB):
    pass 