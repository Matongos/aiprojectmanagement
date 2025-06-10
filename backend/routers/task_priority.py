from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models.task import Task
from schemas.task import Task as TaskSchema, TaskState
from routers.auth import get_current_user
from sqlalchemy import or_, and_, not_

# Define active states
ACTIVE_STATES = ['in_progress', 'changes_requested', 'approved']

router = APIRouter(
    prefix="/task-priority",
    tags=["task-priority"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)

@router.get("/tasks", response_model=List[TaskSchema])
async def get_prioritized_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get prioritized tasks sorted by priority score.
    - For regular users: Returns their assigned tasks
    - For superusers: Returns all tasks in the system
    Only returns tasks in active states (in_progress, changes_requested, approved).
    """
    try:
        # Base query with priority score ordering and active state filtering
        query = (
            db.query(Task)
            .filter(Task.state.in_(ACTIVE_STATES))
            .order_by(Task.priority_score.desc())
        )
        
        # Apply access control based on user type
        if not current_user["is_superuser"]:
            # Regular users see only their assigned tasks
            query = query.filter(
                or_(
                    Task.assigned_to == current_user["id"],
                    Task.created_by == current_user["id"]
                )
            )
        
        # Apply pagination
        tasks = query.offset(skip).limit(limit).all()
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = {
                "id": task.id,
                "name": task.name,
                "description": task.description,
                "priority": task.priority,
                "state": task.state,
                "project_id": task.project_id,
                "stage_id": task.stage_id,
                "assigned_to": task.assigned_to,
                "parent_id": task.parent_id,
                "milestone_id": task.milestone_id,
                "company_id": task.company_id,
                "start_date": task.start_date,
                "end_date": task.end_date,
                "deadline": task.deadline,
                "planned_hours": task.planned_hours,
                "created_by": task.created_by,
                "progress": task.progress if task.progress is not None else 0.0,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "date_last_stage_update": task.date_last_stage_update,
                "priority_score": task.priority_score,
                "priority_reasoning": task.priority_reasoning or [],
                "complexity_score": task.complexity_score,
                "complexity_factors": task.complexity_factors or {},
                "complexity_last_updated": task.complexity_last_updated,
                "assignee": None,
                "milestone": None,
                "company": None,
                "depends_on_ids": [],
                "subtask_ids": [],
                "is_active": True
            }
            
            # Handle assignee
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            
            # Handle milestone
            if hasattr(task, 'milestone') and task.milestone:
                task_dict['milestone'] = {
                    'id': task.milestone.id,
                    'name': task.milestone.name,
                    'description': task.milestone.description,
                    'due_date': task.milestone.due_date.isoformat() if task.milestone.due_date else None,
                    'is_completed': task.milestone.is_completed,
                    'is_active': getattr(task.milestone, 'is_active', True),
                    'project_id': task.milestone.project_id,
                    'created_at': task.milestone.created_at.isoformat() if task.milestone.created_at else None,
                    'created_by': task.milestone.created_by,
                    'updated_at': task.milestone.updated_at.isoformat() if task.milestone.updated_at else None
                }
            
            # Handle company
            if hasattr(task, 'company') and task.company:
                task_dict['company'] = {
                    'id': task.company.id,
                    'name': task.company.name
                }
            
            # Handle dependencies and subtasks
            if hasattr(task, 'depends_on'):
                task_dict['depends_on_ids'] = [dep.id for dep in task.depends_on]
            
            if hasattr(task, 'subtasks'):
                task_dict['subtask_ids'] = [subtask.id for subtask in task.subtasks]
            
            result.append(TaskSchema.model_validate(task_dict))
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching prioritized tasks: {str(e)}"
        )

@router.get("/tasks/project/{project_id}", response_model=List[TaskSchema])
async def get_prioritized_project_tasks(
    project_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get prioritized tasks for a specific project sorted by priority score.
    - For regular users: Returns their assigned tasks in the project
    - For superusers: Returns all tasks in the project
    Only returns tasks in active states (in_progress, changes_requested, approved).
    """
    try:
        # Base query with project filter, active state filtering, and priority score ordering
        query = (
            db.query(Task)
            .filter(
                and_(
                    Task.project_id == project_id,
                    Task.state.in_(ACTIVE_STATES)
                )
            )
            .order_by(Task.priority_score.desc())
        )
        
        # Apply access control based on user type
        if not current_user["is_superuser"]:
            # Regular users see only their assigned tasks
            query = query.filter(
                or_(
                    Task.assigned_to == current_user["id"],
                    Task.created_by == current_user["id"]
                )
            )
        
        # Apply pagination
        tasks = query.offset(skip).limit(limit).all()
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = {
                "id": task.id,
                "name": task.name,
                "description": task.description,
                "priority": task.priority,
                "state": task.state,
                "project_id": task.project_id,
                "stage_id": task.stage_id,
                "assigned_to": task.assigned_to,
                "parent_id": task.parent_id,
                "milestone_id": task.milestone_id,
                "company_id": task.company_id,
                "start_date": task.start_date,
                "end_date": task.end_date,
                "deadline": task.deadline,
                "planned_hours": task.planned_hours,
                "created_by": task.created_by,
                "progress": task.progress if task.progress is not None else 0.0,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "date_last_stage_update": task.date_last_stage_update,
                "priority_score": task.priority_score,
                "priority_reasoning": task.priority_reasoning or [],
                "complexity_score": task.complexity_score,
                "complexity_factors": task.complexity_factors or {},
                "complexity_last_updated": task.complexity_last_updated,
                "assignee": None,
                "milestone": None,
                "company": None,
                "depends_on_ids": [],
                "subtask_ids": [],
                "is_active": True
            }
            
            # Handle assignee
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            
            # Handle milestone
            if hasattr(task, 'milestone') and task.milestone:
                task_dict['milestone'] = {
                    'id': task.milestone.id,
                    'name': task.milestone.name,
                    'description': task.milestone.description,
                    'due_date': task.milestone.due_date.isoformat() if task.milestone.due_date else None,
                    'is_completed': task.milestone.is_completed,
                    'is_active': getattr(task.milestone, 'is_active', True),
                    'project_id': task.milestone.project_id,
                    'created_at': task.milestone.created_at.isoformat() if task.milestone.created_at else None,
                    'created_by': task.milestone.created_by,
                    'updated_at': task.milestone.updated_at.isoformat() if task.milestone.updated_at else None
                }
            
            # Handle company
            if hasattr(task, 'company') and task.company:
                task_dict['company'] = {
                    'id': task.company.id,
                    'name': task.company.name
                }
            
            # Handle dependencies and subtasks
            if hasattr(task, 'depends_on'):
                task_dict['depends_on_ids'] = [dep.id for dep in task.depends_on]
            
            if hasattr(task, 'subtasks'):
                task_dict['subtask_ids'] = [subtask.id for subtask in task.subtasks]
            
            result.append(TaskSchema.model_validate(task_dict))
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching prioritized project tasks: {str(e)}"
        ) 