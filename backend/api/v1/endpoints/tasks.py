from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case, cast, Float
from typing import List
from datetime import datetime, timedelta

from db.session import get_db
from models.task import Task
from models.project import Project
from models.tag import Tag
from schemas.task import TaskAnalytics, TasksByProject, TasksByTag, TaskState
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
        # Get task metrics using SQL aggregation for better performance
        task_metrics = db.query(
            func.sum(Task.planned_hours).label('allocated_time'),
            func.sum(Task.planned_hours).label('total_hours'),
            func.avg(
                case(
                    [(Task.deadline > datetime.utcnow(), 
                      cast(func.extract('day', Task.deadline - datetime.utcnow()), Float))],
                    else_=0
                )
            ).label('days_to_deadline'),
            func.sum(case([(Task.state == TaskState.DONE, Task.planned_hours)], else_=0)).label('hours_spent'),
            func.avg(Task.progress).label('progress')
        ).filter(Task.created_by == current_user.id).first()

        # Calculate derived metrics
        allocated_time = float(task_metrics.allocated_time or 0)
        hours_spent = float(task_metrics.hours_spent or 0)
        total_hours = float(task_metrics.total_hours or 0)
        remaining_hours = total_hours - hours_spent if total_hours > hours_spent else 0
        remaining_percentage = (remaining_hours / total_hours * 100) if total_hours > 0 else 0
        
        # Calculate working hours metrics based on task stages
        working_hours_metrics = db.query(
            func.sum(case([(Task.stage_id == None, Task.planned_hours)], else_=0)).label('hours_to_assign'),
            func.sum(case([(Task.state != TaskState.DONE, Task.planned_hours)], else_=0)).label('hours_to_close')
        ).filter(Task.created_by == current_user.id).first()

        working_hours_to_assign = float(working_hours_metrics.hours_to_assign or 0)
        working_hours_to_close = float(working_hours_metrics.hours_to_close or 0)
        working_days_to_assign = working_hours_to_assign / 8 if working_hours_to_assign else 0
        progress = float(task_metrics.progress or 0)
        days_to_deadline = float(task_metrics.days_to_deadline or 0)

        # Get tasks by project with status counts
        tasks_by_project = (
            db.query(
                Project.name.label('project_name'),
                func.count(Task.id).label('task_count'),
                func.sum(case([(Task.state == TaskState.DONE, 1)], else_=0)).label('completed_count')
            )
            .join(Task, Project.id == Task.project_id)
            .filter(Task.created_by == current_user.id)
            .group_by(Project.name)
            .all()
        )

        # Get tasks by tag with status counts
        tasks_by_tag = (
            db.query(
                Tag.name.label('tag_name'),
                func.count(Task.id).label('task_count'),
                func.sum(case([(Task.state == TaskState.DONE, 1)], else_=0)).label('completed_count')
            )
            .join(Task.tags)
            .filter(Task.created_by == current_user.id)
            .group_by(Tag.name)
            .all()
        )

        return {
            "allocated_time": allocated_time,
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
                {
                    "project_name": p.project_name,
                    "task_count": p.task_count,
                } 
                for p in tasks_by_project
            ],
            "tasks_by_tag": [
                {
                    "tag_name": t.tag_name,
                    "task_count": t.task_count,
                } 
                for t in tasks_by_tag
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch task analytics: {str(e)}"
        ) 