from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from routers.auth import get_current_user
from schemas.user import User
from crud.task_analytics import TaskAnalytics

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)

task_analytics = TaskAnalytics()

@router.get("/project/{project_id}/completion", response_model=Dict[str, Any])
async def get_project_completion_rate(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get the completion rate of tasks in a project."""
    return task_analytics.calculate_project_completion_rate(db=db, project_id=project_id)

@router.get("/project/{project_id}/task-distribution", response_model=List[Dict[str, Any]])
async def get_project_task_distribution(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get the distribution of tasks by status for a project."""
    return task_analytics.get_task_distribution_by_status(db=db, project_id=project_id)

@router.get("/user/productivity", response_model=Dict[str, Any])
async def get_user_productivity(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get productivity metrics for the current user."""
    return task_analytics.get_user_productivity(db=db, user_id=current_user["id"], days=days)

@router.get("/user/{user_id}/productivity", response_model=Dict[str, Any])
async def get_specific_user_productivity(
    user_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get productivity metrics for a specific user. Only available to superusers."""
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=403, 
            detail="Not enough permissions to view other users' productivity"
        )
    
    return task_analytics.get_user_productivity(db=db, user_id=user_id, days=days)

@router.get("/tasks/summary", response_model=Dict[str, Any])
async def get_task_analytics_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get overall task analytics summary."""
    return task_analytics.get_task_analytics_summary(db=db, current_user_id=current_user["id"])

@router.get("/tasks/trend", response_model=List[Dict[str, Any]])
async def get_task_trend_data(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get task creation and completion trend data."""
    return task_analytics.get_task_trend_data(db=db, days=days) 