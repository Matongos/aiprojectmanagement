from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from routers.auth import get_current_user
from models.user import User
from services.task_analysis_service import analyze_project_tasks
from schemas.task_analysis import TaskAnalysisResponse

router = APIRouter(
    prefix="/api/task-analysis",
    tags=["task-analysis"]
)

@router.get("/projects/{project_id}/analysis", response_model=TaskAnalysisResponse)
async def analyze_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze all tasks in a project using AI to generate insights and recommendations.
    
    This endpoint will:
    - Analyze task completion and progress
    - Identify tasks at risk
    - Assess workload distribution
    - Generate AI-powered insights
    - Provide recommendations
    
    Returns a comprehensive analysis of the project's tasks.
    """
    try:
        return analyze_project_tasks(db, project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing tasks: {str(e)}") 