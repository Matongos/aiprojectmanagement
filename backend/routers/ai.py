from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db
from services.ai_service import get_ai_service, AIService
from services.ollama_client import get_ollama_client
from routers.auth import get_current_user
from services.project_service import ProjectService

router = APIRouter(prefix="/ai", tags=["ai"], dependencies=[Depends(get_current_user)])

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

class ProjectInsight(BaseModel):
    summary: str
    completion_percentage: float
    risks: List[str]
    suggestions: List[str]
    workload_analysis: Dict[str, Any]
    timeline_status: str
    critical_tasks: List[Dict[str, Any]]
    resource_allocation: Dict[str, Any]
    performance_metrics: Dict[str, Any]



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

@router.get("/projects/{project_id}/insights", response_model=ProjectInsight)
async def generate_project_insights(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate AI-powered insights for a project"""
    ai_service = AIService(db)
    project_service = ProjectService()

    # Verify project access
    if not project_service.can_access_project(db, current_user["id"], project_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this project")

    return await ai_service.analyze_project_insights(project_id)

# Export the get_ollama_client function
__all__ = ['router', 'get_ollama_client'] 