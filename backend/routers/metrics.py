from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime, timedelta

from database import get_db
from models.metrics import ProjectMetrics, TaskMetrics, ResourceMetrics
from models.project import Project
from models.task import Task
from models.user import User
from schemas.metrics import (
    ProjectMetrics as ProjectMetricsSchema,
    TaskMetrics as TaskMetricsSchema,
    ResourceMetrics as ResourceMetricsSchema
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
    dependencies=[Depends(get_current_user)],
)

@router.get("/task/{task_id}")
async def get_task_metrics(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get metrics for a specific task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if not task.metrics:
        return {
            "state_changes": [],
            "actual_duration": 0,
            "time_estimate_accuracy": 0,
            "dependency_count": 0,
            "comment_count": 0,
            "idle_time": 0,
            "review_iterations": 0,
            "bug_count": 0,
            "rework_hours": 0,
            "complexity_score": 0,
            "handover_count": 0,
            "blocked_time": 0
        }
        
    return {
        "state_changes": task.metrics.state_changes,
        "actual_duration": task.metrics.actual_duration,
        "time_estimate_accuracy": task.metrics.time_estimate_accuracy,
        "dependency_count": task.metrics.dependency_count,
        "comment_count": task.metrics.comment_count,
        "idle_time": task.metrics.idle_time,
        "review_iterations": task.metrics.review_iterations,
        "bug_count": task.metrics.bug_count,
        "rework_hours": task.metrics.rework_hours,
        "complexity_score": task.metrics.complexity_score,
        "handover_count": task.metrics.handover_count,
        "blocked_time": task.metrics.blocked_time
    }

@router.get("/project/{project_id}")
async def get_project_metrics(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get aggregated metrics for a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.state == "done"])
    total_duration = sum(t.metrics.actual_duration for t in tasks if t.metrics)
    avg_completion_time = total_duration / completed_tasks if completed_tasks > 0 else 0
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "completion_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
        "average_completion_time": avg_completion_time,
        "tasks_by_state": {
            state: len([t for t in tasks if t.state == state])
            for state in set(t.state for t in tasks)
        }
    }

@router.get("/user/{user_id}")
async def get_user_metrics(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get metrics for a specific user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    assigned_tasks = db.query(Task).filter(Task.assigned_to == user_id).all()
    completed_tasks = [t for t in assigned_tasks if t.state == "done"]
    
    return {
        "total_assigned_tasks": len(assigned_tasks),
        "completed_tasks": len(completed_tasks),
        "completion_rate": len(completed_tasks) / len(assigned_tasks) if assigned_tasks else 0,
        "average_completion_time": sum(t.metrics.actual_duration for t in completed_tasks if t.metrics) / len(completed_tasks) if completed_tasks else 0,
        "tasks_by_state": {
            state: len([t for t in assigned_tasks if t.state == state])
            for state in set(t.state for t in assigned_tasks)
        }
    }

@router.get("/project/{project_id}/resources", response_model=List[ResourceMetricsSchema])
def get_project_resource_metrics(project_id: int, db: Session = Depends(get_db)):
    """Get resource metrics for all members of a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project.resource_metrics

@router.get("/project/{project_id}/summary")
def get_project_metrics_summary(project_id: int, db: Session = Depends(get_db)):
    """Get a comprehensive summary of project metrics"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update all metrics
    project.update_metrics()
    for task in project.tasks:
        task.update_metrics()
    db.commit()
    
    # Calculate summary statistics
    total_tasks = len(project.tasks)
    completed_tasks = sum(1 for task in project.tasks if task.state == 'done')
    total_time = sum(task.metrics.actual_duration for task in project.tasks if task.metrics)
    
    return {
        "project_metrics": project.metrics,
        "summary": {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
            "total_time_spent": total_time,
            "average_task_duration": total_time / total_tasks if total_tasks > 0 else 0
        },
        "task_metrics": [task.metrics for task in project.tasks if task.metrics],
        "resource_metrics": project.resource_metrics
    }

def update_all_metrics(db: Session):
    """Background task to update all metrics"""
    projects = db.query(Project).all()
    for project in projects:
        project.update_metrics()
        for task in project.tasks:
            task.update_metrics()
    db.commit()

@router.post("/update-all")
def trigger_metrics_update(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger a background update of all metrics"""
    background_tasks.add_task(update_all_metrics, db)
    return {"message": "Metrics update scheduled"} 