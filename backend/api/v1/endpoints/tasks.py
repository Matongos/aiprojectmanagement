from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from db.session import get_db
from models.task import Task
from models.project import Project
from models.tag import Tag
from schemas.task import TaskAnalytics, TasksByProject, TasksByTag
from core.auth import get_current_user

router = APIRouter()

@router.get("/analysis", response_model=TaskAnalytics)
async def get_task_analysis(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get comprehensive task analysis including time metrics and distributions
    """
    try:
        # Get all tasks for the current user
        tasks = db.query(Task).filter(Task.user_id == current_user.id).all()
        
        # Calculate time-based metrics
        total_hours = sum(task.allocated_hours for task in tasks if task.allocated_hours)
        hours_spent = sum(task.hours_spent for task in tasks if task.hours_spent)
        remaining_hours = total_hours - hours_spent if total_hours > hours_spent else 0
        remaining_percentage = (remaining_hours / total_hours * 100) if total_hours > 0 else 0
        
        # Calculate progress and deadline metrics
        now = datetime.utcnow()
        tasks_with_deadline = [task for task in tasks if task.deadline]
        days_to_deadline = sum(
            (task.deadline - now).days 
            for task in tasks_with_deadline 
            if task.deadline > now
        ) / len(tasks_with_deadline) if tasks_with_deadline else 0
        
        # Calculate working hours metrics
        working_hours_to_assign = sum(task.working_hours_to_assign for task in tasks if task.working_hours_to_assign)
        working_hours_to_close = sum(task.working_hours_to_close for task in tasks if task.working_hours_to_close)
        working_days_to_assign = working_hours_to_assign / 8 if working_hours_to_assign else 0
        
        # Calculate average progress
        progress = sum(task.progress for task in tasks if task.progress) / len(tasks) if tasks else 0
        
        # Get tasks by project
        tasks_by_project = (
            db.query(
                Project.name.label('project_name'),
                func.count(Task.id).label('task_count')
            )
            .join(Task)
            .filter(Task.user_id == current_user.id)
            .group_by(Project.name)
            .all()
        )
        
        # Get tasks by tag
        tasks_by_tag = (
            db.query(
                Tag.name.label('tag_name'),
                func.count(Task.id).label('task_count')
            )
            .join(Task.tags)
            .filter(Task.user_id == current_user.id)
            .group_by(Tag.name)
            .all()
        )
        
        return {
            "allocated_time": total_hours,
            "days_to_deadline": days_to_deadline,
            "hours_spent": hours_spent,
            "progress": progress,
            "remaining_hours": remaining_hours,
            "remaining_hours_percentage": remaining_percentage,
            "total_hours": total_hours,
            "working_days_to_assign": working_days_to_assign,
            "working_hours_to_assign": working_hours_to_assign,
            "working_hours_to_close": working_hours_to_close,
            "tasks_by_project": [
                {"project_name": p[0], "task_count": p[1]} 
                for p in tasks_by_project
            ],
            "tasks_by_tag": [
                {"tag_name": t[0], "task_count": t[1]} 
                for t in tasks_by_tag
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch task analytics: {str(e)}"
        ) 