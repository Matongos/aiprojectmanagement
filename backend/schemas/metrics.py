from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class ProjectMetricsBase(BaseModel):
    schedule_variance: float = 0.0
    milestone_completion_rate: float = 0.0
    budget_utilization: float = 0.0
    cost_variance: float = 0.0
    defect_density: float = 0.0
    rework_rate: float = 0.0
    velocity: float = 0.0
    throughput: float = 0.0
    resource_utilization: float = 0.0
    team_load: float = 0.0

class ProjectMetricsCreate(ProjectMetricsBase):
    project_id: int

class ProjectMetrics(ProjectMetricsBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

class TaskMetricsBase(BaseModel):
    actual_duration: float = 0.0
    time_estimate_accuracy: float = 0.0
    idle_time: float = 0.0
    review_iterations: int = 0
    bug_count: int = 0
    rework_hours: float = 0.0
    complexity_score: float = 0.0
    dependency_count: int = 0
    handover_count: int = 0
    comment_count: int = 0
    state_changes: List[Dict] = []
    blocked_time: float = 0.0

class TaskMetricsCreate(TaskMetricsBase):
    task_id: int

class TaskMetrics(TaskMetricsBase):
    id: int
    task_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

class ResourceMetricsBase(BaseModel):
    billable_hours: float = 0.0
    availability_rate: float = 0.0
    overtime_hours: float = 0.0
    task_completion_rate: float = 0.0
    average_task_duration: float = 0.0
    productivity_score: float = 0.0
    skill_utilization: Dict = {}
    learning_curve: float = 0.0
    collaboration_score: float = 0.0
    response_time: float = 0.0

class ResourceMetricsCreate(ResourceMetricsBase):
    user_id: int
    project_id: int

class ResourceMetrics(ResourceMetricsBase):
    id: int
    user_id: int
    project_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True 