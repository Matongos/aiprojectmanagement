from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class TaskRisk(BaseModel):
    """Represents a risk identified for a task"""
    task_id: int
    task_name: str
    risk_type: str  # e.g. 'overdue', 'unassigned', 'blocked', etc.
    risk_level: str  # 'low', 'medium', 'high'
    description: str
    suggested_action: Optional[str] = None

class WorkloadInfo(BaseModel):
    """Represents workload information for a user"""
    user_id: int
    user_name: str
    assigned_tasks: int
    total_hours: float
    overdue_tasks: int
    upcoming_deadlines: int
    workload_status: str  # 'underutilized', 'balanced', 'overloaded'

class ProjectInsight(BaseModel):
    """Represents an AI-generated insight about the project"""
    insight_type: str  # e.g. 'risk', 'suggestion', 'observation'
    description: str
    importance: str  # 'low', 'medium', 'high'
    action_required: bool

class TaskAnalysisResponse(BaseModel):
    """Main response schema for task analysis"""
    project_id: int
    analysis_timestamp: datetime
    
    # Overall metrics
    completion_percentage: float = Field(..., ge=0, le=100)
    total_tasks: int
    active_tasks: int
    completed_tasks: int
    overdue_tasks: int
    
    # Risk assessment
    overall_risk_level: str  # 'low', 'medium', 'high'
    risk_factors: List[TaskRisk]
    
    # Workload analysis
    team_workload: List[WorkloadInfo]
    workload_distribution_score: float = Field(..., ge=0, le=1)
    
    # Timeline
    estimated_completion_date: Optional[datetime]
    delay_probability: float = Field(..., ge=0, le=1)
    
    # AI Insights
    insights: List[ProjectInsight]
    recommendations: List[str]

    class Config:
        from_attributes = True 