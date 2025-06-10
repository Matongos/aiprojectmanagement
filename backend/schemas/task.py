from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from .file_attachment import FileAttachment
from .milestone import MilestoneResponse
from .tag import Tag
from enum import Enum

class TaskState(str, Enum):
    NULL = "null"
    IN_PROGRESS = "in_progress"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    CANCELED = "canceled"
    DONE = "done"

class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class UserBase(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    profile_image_url: Optional[str] = None

    class Config:
        from_attributes = True

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
    state: Optional[TaskState] = Field(default=TaskState.NULL, description="Task state")
    project_id: int = Field(..., description="Project ID (required)")
    stage_id: int = Field(..., description="Stage ID (required)")
    parent_id: Optional[int] = Field(default=None, description="Parent task ID")
    assigned_to: Optional[int] = Field(default=None, description="Assignee user ID")
    milestone_id: Optional[int] = Field(default=None, description="Milestone ID")
    company_id: Optional[int] = Field(default=None, description="Company ID")
    start_date: Optional[datetime] = Field(default=None, description="Task start date")
    end_date: Optional[datetime] = Field(default=None, description="Task end date")
    deadline: Optional[datetime] = Field(default=None, description="Task deadline")
    planned_hours: Optional[float] = Field(default=0.0, ge=0, description="Planned hours for the task")
    tag_ids: Optional[List[int]] = Field(default=[], description="List of tag IDs")
    status: Optional[str] = Field(default="in_progress", description="Task status")
    estimated_hours: Optional[float] = Field(default=0.0, ge=0, description="Estimated hours for the task")
    tags: Optional[str] = Field(default="", description="Task tags")
    created_by: Optional[int] = Field(default=None, description="User ID who created the task")
    is_recurring: Optional[bool] = Field(default=False, description="Whether task is recurring")

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
    milestone_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    planned_hours: Optional[float] = Field(None, ge=0)
    tag_ids: Optional[List[int]] = None

class Task(TaskBase):
    id: int
    created_by: int
    progress: Optional[float] = Field(default=0.0)
    created_at: datetime
    updated_at: Optional[datetime]
    date_last_stage_update: Optional[datetime] = None
    priority_source: Optional[str] = Field(default="auto", description="Source of the priority (auto/manual/rule/ai)")
    priority_score: Optional[float] = Field(default=0.0, description="Priority score from 0.0 to 1.0")
    priority_reasoning: Optional[List[str]] = Field(default_factory=list, description="List of reasons for the priority")
    complexity_score: Optional[float] = Field(default=0.0, description="Overall task complexity score")
    complexity_factors: Optional[dict] = Field(default_factory=dict, description="Detailed breakdown of complexity factors")
    complexity_last_updated: Optional[datetime] = Field(default=None, description="When complexity was last calculated")
    depends_on_ids: List[int] = []
    subtask_ids: List[int] = []
    attachments: Optional[List[FileAttachment]] = None
    milestone: Optional[dict] = {
        'id': int,
        'name': str,
        'description': Optional[str],
        'due_date': Optional[str],
        'is_completed': bool,
        'is_active': bool,
        'project_id': int,
        'created_at': datetime,
        'created_by': Optional[int],
        'updated_at': Optional[datetime]
    }
    company: Optional[dict] = None
    assignee: Optional[dict] = None
    tags: Optional[List[Tag]] = Field(default=[], description="List of associated tags")
    is_active: bool = Field(default=True, description="Whether task is active")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    def dict(self, *args, **kwargs):
        """Override dict method to properly handle serialization"""
        d = super().dict(*args, **kwargs)
        if self.milestone:
            d['milestone'] = {
                'id': self.milestone.id,
                'name': self.milestone.name,
                'description': self.milestone.description,
                'due_date': self.milestone.due_date.isoformat() if self.milestone.due_date else None,
                'is_completed': self.milestone.is_completed,
                'is_active': self.milestone.is_active,
                'project_id': self.milestone.project_id,
                'created_at': self.milestone.created_at.isoformat() if self.milestone.created_at else None,
                'created_by': self.milestone.created_by,
                'updated_at': self.milestone.updated_at.isoformat() if self.milestone.updated_at else None
            }
        if self.assignee:
            d['assignee'] = {
                'id': self.assignee.id,
                'username': self.assignee.username,
                'email': self.assignee.email,
                'full_name': self.assignee.full_name,
                'profile_image_url': getattr(self.assignee, 'profile_image_url', None)
            }
        return d

class TaskResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    state: str
    priority: str
    priority_score: float = Field(default=0.0)
    priority_reasoning: List[str] = Field(default_factory=list)
    deadline: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    project_id: int
    assigned_to: Optional[int] = None
    created_by: int
    complexity_score: Optional[float] = Field(default=0.0, description="Overall task complexity score")
    complexity_factors: Optional[dict] = Field(default_factory=dict, description="Detailed breakdown of complexity factors")
    complexity_last_updated: Optional[datetime] = Field(default=None, description="When complexity was last calculated")

    class Config:
        from_attributes = True

class TaskStageWithTasks(TaskStage):
    """Task stage schema that includes the tasks in the stage"""
    tasks: List[TaskResponse] = []

    class Config:
        from_attributes = True

class TasksByProject(BaseModel):
    project_name: str
    task_count: int

class TasksByTag(BaseModel):
    tag_name: str
    task_count: int

class TaskAnalytics(BaseModel):
    allocated_time: float
    days_to_deadline: float
    hours_spent: float
    progress: float
    remaining_hours: float
    remaining_hours_percentage: float
    total_hours: float
    working_days_to_assign: float
    working_hours_to_assign: float
    working_hours_to_close: float
    tasks_by_project: List[TasksByProject]
    tasks_by_tag: List[TasksByTag]

    class Config:
        from_attributes = True 