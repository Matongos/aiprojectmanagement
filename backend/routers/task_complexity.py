from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from database import get_db
from services.complexity_service import ComplexityService
from schemas.task_complexity import TaskComplexityResponse, TaskComplexityAnalysis
from routers.auth import get_current_user
from models.task import Task
from datetime import datetime
from pydantic import BaseModel
from tasks.task_complexity import calculate_task_complexity_task
from celery.result import AsyncResult

class StoredComplexityResponse(BaseModel):
    task_id: int
    complexity_score: float
    complexity_factors: Dict
    complexity_last_updated: datetime | None
    task_name: str
    task_description: str | None

router = APIRouter(
    prefix="/task-complexity",
    tags=["task-complexity"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)

complexity_service = ComplexityService()

@router.get("/{task_id}", response_model=Dict)
async def get_task_complexity(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    celery_task = calculate_task_complexity_task.delay(task_id)
    return {
        "status": "queued",
        "task_id": task_id,
        "celery_task_id": celery_task.id
    }

@router.get("/batch/{project_id}", response_model=List[TaskComplexityResponse])
async def get_project_tasks_complexity(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Calculate complexity scores for all tasks in a project"""
    from models.task import Task
    
    try:
        # Get all tasks in the project
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
        if not tasks:
            raise HTTPException(
                status_code=404,
                detail=f"No tasks found for project {project_id}"
            )

        # Calculate complexity for each task
        results = []
        for task in tasks:
            try:
                complexity = await complexity_service.analyze_task_complexity(db, task.id)
                results.append(TaskComplexityResponse(
                    success=True,
                    complexity=complexity
                ))
            except Exception as e:
                results.append(TaskComplexityResponse(
                    success=False,
                    complexity=None,
                    message=f"Error analyzing task {task.id}: {str(e)}"
                ))

        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating project tasks complexity: {str(e)}"
        )

@router.get("/stored/{task_id}", response_model=StoredComplexityResponse)
async def get_stored_task_complexity(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch stored complexity data for a task without recalculating.
    Returns the last calculated complexity score and factors.
    """
    try:
        # Get the task with its stored complexity data
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return StoredComplexityResponse(
            task_id=task.id,
            complexity_score=task.complexity_score,
            complexity_factors=task.complexity_factors or {},
            complexity_last_updated=task.complexity_last_updated,
            task_name=task.name,
            task_description=task.description
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stored task complexity: {str(e)}"
        )

@router.get("/stored", response_model=List[StoredComplexityResponse])
async def get_all_stored_task_complexities(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch stored complexity data for all tasks without recalculating.
    Returns a list of tasks with their last calculated complexity scores and factors.
    """
    try:
        # Get all tasks with their stored complexity data
        tasks = db.query(Task).offset(skip).limit(limit).all()
        
        return [
            StoredComplexityResponse(
                task_id=task.id,
                complexity_score=task.complexity_score,
                complexity_factors=task.complexity_factors or {},
                complexity_last_updated=task.complexity_last_updated,
                task_name=task.name,
                task_description=task.description
            )
            for task in tasks
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stored task complexities: {str(e)}"
        )

@router.get("/status/{celery_task_id}", response_model=Dict)
async def get_task_complexity_status(
    celery_task_id: str
):
    result = AsyncResult(celery_task_id)
    response = {
        "task_id": celery_task_id,
        "state": result.state,
        "result": result.result if result.ready() else None
    }
    return response 