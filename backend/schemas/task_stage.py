from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from .task import TaskResponse

class TaskStageBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sequence: int = Field(default=1, ge=0)
    description: Optional[str] = None
    fold: bool = Field(default=False, description="Whether stage is folded in Kanban view")
    is_active: bool = Field(default=True)
    project_id: Optional[int] = None

class TaskStageCreate(TaskStageBase):
    project_id: int

class TaskStageUpdate(TaskStageBase):
    pass

class TaskStageWithTasks(TaskStageBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    tasks: List[TaskResponse] = []

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    def dict(self, *args, **kwargs):
        """Override dict method to properly handle serialization"""
        d = super().dict(*args, **kwargs)
        if self.tasks:
            d['tasks'] = [
                {
                    **task.dict(),
                    'assignee': task.assignee_data if hasattr(task, 'assignee_data') else task.assignee
                }
                for task in self.tasks
            ]
        return d

class TaskStage(TaskStageBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    auto_progress_percentage: float = 0.0

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        } 