from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from services.complexity_service import ComplexityService
from schemas.task_complexity import TaskComplexityResponse, TaskComplexityAnalysis
from routers.auth import get_current_user

router = APIRouter(
    prefix="/task-complexity",
    tags=["task-complexity"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)

complexity_service = ComplexityService()

@router.get("/{task_id}", response_model=TaskComplexityResponse)
async def get_task_complexity(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate complexity score for a specific task.
    
    The complexity score is calculated based on:
    - Task name and description analysis
    - Time pressure and deadlines
    - Environmental factors (indoor/outdoor)
    - Weather conditions (for outdoor tasks)
    - Dependencies
    """
    try:
        complexity = await complexity_service.analyze_task_complexity(db, task_id)
        return TaskComplexityResponse(
            success=True,
            complexity=complexity
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating task complexity: {str(e)}"
        )

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