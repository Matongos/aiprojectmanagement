from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db
from services.ai_service import get_ai_service
from services.ollama_client import get_ollama_client
from routers.auth import get_current_user

router = APIRouter(prefix="/ai", tags=["ai"])

class TaskPatterns(BaseModel):
    type: str = Field(default="unknown")
    common_issues: List[str] = Field(default_factory=list)
    success_factors: List[str] = Field(default_factory=list)

class TaskAnalysis(BaseModel):
    complexity: int = Field(ge=1, le=10)
    risk_factors: List[str]
    time_accuracy: float = Field(ge=0.0, le=1.0)
    suggestions: List[str]
    patterns: TaskPatterns

class ProjectRiskAnalysis(BaseModel):
    risk_level: int
    risk_factors: List[str]
    mitigations: List[str]
    timeline_status: str
    resource_recommendations: List[str]

@router.get("/tasks/{task_id}/analyze", response_model=TaskAnalysis)
async def analyze_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get AI analysis for a task"""
    ai_service = get_ai_service(db)
    analysis = await ai_service.analyze_task(task_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Task not found")
    return analysis

@router.get("/tasks/{task_id}/suggest-priority")
async def suggest_task_priority(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get AI-suggested priority for a task"""
    ai_service = get_ai_service(db)
    priority = await ai_service.suggest_task_priority(task_id)
    return {"priority": priority}

@router.get("/tasks/{task_id}/estimate-time")
async def estimate_task_time(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get AI-estimated completion time for a task"""
    ai_service = get_ai_service(db)
    estimated_hours = await ai_service.estimate_completion_time(task_id)
    return {"estimated_hours": estimated_hours}

@router.get("/projects/{project_id}/risks", response_model=ProjectRiskAnalysis)
async def analyze_project_risks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get AI risk analysis for a project"""
    ai_service = get_ai_service(db)
    analysis = await ai_service.analyze_project_risks(project_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Project not found")
    return analysis

# Export the get_ollama_client function
__all__ = ['router', 'get_ollama_client'] 