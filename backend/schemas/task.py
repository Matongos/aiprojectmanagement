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
    name: str = Field(..., min_length=1, max_length=255, description="Task name (required)")
    description: Optional[str] = Field(default="", description="Task description")
    priority: Optional[TaskPriority] = Field(default=TaskPriority.NORMAL, description="Task priority")
    state: Optional[TaskState] = Field(default=TaskState.DRAFT, description="Task state")
    project_id: int = Field(..., description="Project ID (required)")
    stage_id: int = Field(..., description="Stage ID (required)")
    parent_id: Optional[int] = Field(default=None, description="Parent task ID")
    assigned_to: Optional[int] = Field(default=None, description="Assignee user ID")
    milestone_id: Optional[int] = Field(default=None, description="Milestone ID")
    company_id: Optional[int] = Field(default=None, description="Company ID")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    planned_hours: Optional[float] = Field(default=0.0, ge=0)

class TaskCreate(TaskBase):
    """Task creation schema with required fields:
    - name: Task name
    - project_id: Project ID
    - stage_id: Stage ID
    """
    pass

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
    progress: Optional[float] = Field(default=0.0)
    created_at: datetime
    updated_at: Optional[datetime]
    date_last_stage_update: Optional[datetime] = None
    depends_on_ids: List[int] = []
    subtask_ids: List[int] = []
    attachments: Optional[List[FileAttachment]] = None
    milestone: Optional[dict] = None  # Will include milestone details if available
    company: Optional[dict] = None    # Will include company details if available
    assignee: Optional[dict] = None   # Will include assignee details if available

    class Config:
        from_attributes = True

class TaskStageWithTasks(TaskStage):
    """Task stage schema that includes the tasks in the stage"""
    tasks: List[Task] = []

    class Config:
        from_attributes = True 