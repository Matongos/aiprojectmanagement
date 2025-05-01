from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from .file_attachment import FileAttachment
from enum import Enum

class TaskState(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELED = "canceled"

class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class TaskStageBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    sequence: int = 1
    fold: bool = False
    is_closed: bool = False
    project_id: int

class TaskStageCreate(TaskStageBase):
    pass

class TaskStageUpdate(TaskStageBase):
    pass

class TaskStage(TaskStageBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = Field(default=TaskPriority.NORMAL)
    state: Optional[TaskState] = Field(default=TaskState.DRAFT)
    project_id: int
    stage_id: Optional[int] = None
    parent_id: Optional[int] = None
    assigned_to: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    planned_hours: Optional[float] = Field(default=0.0, ge=0)

class TaskCreate(TaskBase):
    project_id: int  # Only project_id is required in addition to name

class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    state: Optional[TaskState] = None
    project_id: Optional[int] = None
    stage_id: Optional[int] = None
    parent_id: Optional[int] = None
    assigned_to: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    planned_hours: Optional[float] = Field(None, ge=0)

class Task(TaskBase):
    id: int
    created_by: int
    progress: float = 0.0
    created_at: datetime
    updated_at: Optional[datetime]
    date_last_stage_update: Optional[datetime] = None
    depends_on_ids: List[int] = []
    subtask_ids: List[int] = []
    attachments: Optional[List[FileAttachment]] = None

    class Config:
        from_attributes = True 