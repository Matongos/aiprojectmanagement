from typing import Optional, Literal, List
from datetime import datetime
from pydantic import BaseModel, Field
from .file_attachment import FileAttachment

# Define task status and priority as literals
TaskStatus = Literal["todo", "in_progress", "review", "done", "cancelled"]
TaskPriority = Literal["low", "medium", "high", "urgent"]

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    due_date: Optional[datetime] = None
    estimated_hours: Optional[int] = None
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
    created_by: int
    assignee_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Task(TaskInDB):
    attachments: Optional[List[FileAttachment]] = None 