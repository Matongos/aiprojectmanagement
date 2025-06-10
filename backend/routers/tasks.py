from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date, timezone
import logging
from models.task import Task as TaskModel
from models.task_stage import TaskStage
from models.user import User
from schemas.task import TaskCreate, TaskUpdate, Task as TaskSchema, TaskState, TaskPriority
from schemas.file_attachment import FileAttachment as FileAttachmentSchema, FileAttachmentCreate
from crud import task as task_crud
from crud import file_attachment as file_attachment_crud
from crud import activity
from crud.tag import tag as tag_crud
from schemas.activity import ActivityCreate
from database import get_db
from routers.auth import get_current_user
from schemas.user import User as UserSchema
from services.file_service import FileService
from services.notification_service import NotificationService
from services.task_service import TaskService
from services.priority_service import PriorityService
from services.complexity_service import ComplexityService
from models.project import Project
from schemas.tag import Tag as TagSchema
from services.permission_service import PermissionService
from services.priority_scoring_service import PriorityScoringService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)

# File attachment endpoints
file_service = FileService()
task_service = TaskService()
notification_service = NotificationService()

@router.post("/", response_model=Dict[str, Any])
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new task"""
    try:
        task_service = TaskService()
        created_task = task_service.create_task(db, task_data, current_user["id"])

        # Calculate initial complexity
        await created_task.update_metrics()
        db.commit()
        
        # Convert to dictionary and add additional fields
        task_dict = {
            "id": created_task.id,
            "title": created_task.name,
            "description": created_task.description,
            "state": created_task.state,
            "priority": created_task.priority,
            "deadline": created_task.deadline,
            "planned_hours": created_task.planned_hours,
            "assigned_to": created_task.assigned_to,
            "created_by": created_task.created_by,
            "project_id": created_task.project_id,
            "created_at": created_task.created_at,
            "updated_at": created_task.updated_at,
            "progress": created_task.progress,
            "stage_id": created_task.stage_id
        }
        
        return task_dict
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[TaskSchema])
async def read_tasks(
    project_id: Optional[int] = None,
    stage_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get tasks with optional filtering"""
    try:
        if project_id:
            tasks = task_crud.get_by_project(db, project_id=project_id, skip=skip, limit=limit)
        elif stage_id:
            tasks = task_crud.get_tasks_by_stage(db, stage_id=stage_id, skip=skip, limit=limit)
        elif search:
            tasks = task_crud.search_tasks(db, search_term=search, skip=skip, limit=limit)
        else:
            tasks = task_crud.get_user_tasks(db, current_user["id"], skip=skip, limit=limit)
            
        if not current_user["is_superuser"]:
            tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            # Create base task dictionary
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
                "assignee": None,
                "milestone": None,
                "company": None,
                "depends_on_ids": [],
                "subtask_ids": []
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
                    'is_active': getattr(task.milestone, 'is_active', True)
                }
            
            # Handle company
            if hasattr(task, 'company') and task.company:
                task_dict['company'] = {
                    'id': task.company.id,
                    'name': task.company.name
                }
            
            # Handle dependencies and subtasks
            if hasattr(task, 'depends_on') and task.depends_on:
                task_dict["depends_on_ids"] = [dep.id for dep in task.depends_on]
            
            if hasattr(task, 'children') and task.children:
                task_dict["subtask_ids"] = [child.id for child in task.children]
            
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tasks: {str(e)}"
        )

@router.get("/my", response_model=List[TaskSchema])
async def read_my_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tasks assigned to or created by the current user"""
    try:
        tasks = task_crud.get_user_tasks(db, current_user["id"], skip, limit)
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            # Create base task dictionary
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
                "assignee": None,
                "milestone": None,
                "company": None,
                "depends_on_ids": [],
                "subtask_ids": [],
                "attachments": []
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
                    'is_active': getattr(task.milestone, 'is_active', True)
                }
            
            # Handle company
            if hasattr(task, 'company') and task.company:
                task_dict['company'] = {
                    'id': task.company.id,
                    'name': task.company.name
                }
            
            # Handle dependencies and subtasks
            if hasattr(task, 'depends_on') and task.depends_on:
                task_dict["depends_on_ids"] = [dep.id for dep in task.depends_on]
            
            if hasattr(task, 'children') and task.children:
                task_dict["subtask_ids"] = [child.id for child in task.children]
            
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user tasks: {str(e)}"
        )

@router.get("/{task_id}", response_model=TaskSchema)
async def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get a specific task by ID."""
    try:
        db_task = task_crud.get(db=db, id=task_id)
        if db_task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if not current_user["is_superuser"] and db_task.assigned_to != current_user["id"] and db_task.created_by != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        # Serialize the task manually to avoid pydantic validation issues with the User object
        task_data = {
            "id": db_task.id,
            "name": db_task.name,
            "description": db_task.description,
            "priority": db_task.priority,
            "priority_source": db_task.priority_source,
            "priority_score": db_task.priority_score,
            "priority_reasoning": db_task.priority_reasoning or [],
            "state": db_task.state,
            "project_id": db_task.project_id,
            "stage_id": db_task.stage_id,
            "assigned_to": db_task.assigned_to,
            "parent_id": db_task.parent_id,
            "milestone_id": db_task.milestone_id,
            "company_id": db_task.company_id,
            "start_date": db_task.start_date,
            "end_date": db_task.end_date,
            "deadline": db_task.deadline,
            "planned_hours": db_task.planned_hours,
            "created_by": db_task.created_by,
            "progress": db_task.progress,
            "created_at": db_task.created_at,
            "updated_at": db_task.updated_at,
            "date_last_stage_update": db_task.date_last_stage_update,
            "assignee": None,
            "milestone": None,
            "company": None,
            "depends_on_ids": [],
            "subtask_ids": [],
            "attachments": []
        }
        
        # Handle assignee
        if hasattr(db_task, 'assignee') and db_task.assignee:
            task_data["assignee"] = {
                'id': db_task.assignee.id,
                'username': db_task.assignee.username,
                'email': db_task.assignee.email,
                'full_name': db_task.assignee.full_name,
                'profile_image_url': getattr(db_task.assignee, 'profile_image_url', None)
            }
        
        # Handle milestone
        if hasattr(db_task, 'milestone') and db_task.milestone:
            task_data["milestone"] = {
                'id': db_task.milestone.id,
                'name': db_task.milestone.name,
                'description': db_task.milestone.description,
                'due_date': db_task.milestone.due_date.isoformat() if db_task.milestone.due_date else None,
                'is_completed': db_task.milestone.is_completed,
                'is_active': getattr(db_task.milestone, 'is_active', True)
            }
        
        # Handle company
        if hasattr(db_task, 'company') and db_task.company:
            task_data["company"] = {
                'id': db_task.company.id,
                'name': db_task.company.name
            }
        
        # Handle dependencies and subtasks
        if hasattr(db_task, 'depends_on') and db_task.depends_on:
            task_data["depends_on_ids"] = [dep.id for dep in db_task.depends_on]
        
        if hasattr(db_task, 'children') and db_task.children:
            task_data["subtask_ids"] = [child.id for child in db_task.children]
        
        # Handle attachments
        if hasattr(db_task, 'attachments') and db_task.attachments:
            attach_data = []
            for attachment in db_task.attachments:
                attach_data.append({
                    'id': attachment.id,
                    'filename': attachment.filename,
                    'original_filename': attachment.original_filename,
                    'file_size': attachment.file_size,
                    'content_type': attachment.content_type,
                    'description': attachment.description,
                    'task_id': attachment.task_id,
                    'created_at': attachment.created_at.isoformat() if attachment.created_at else None,
                    'created_by': attachment.created_by
                })
            task_data["attachments"] = attach_data
        
        # Now create a TaskSchema from our manually constructed dict
        return TaskSchema.model_validate(task_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching task: {str(e)}"
        )

@router.put("/{task_id}", response_model=Dict[str, Any])
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a task"""
    try:
        task_service = TaskService()
        
        # Get the task first to check permissions
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Convert task_data to dict and ensure state is properly handled
        update_data = task_data.model_dump(exclude_unset=True)
        
        # Special permission check for priority updates
        if "priority" in update_data:
            permission_service = PermissionService()
            if not permission_service.can_modify_project(db, current_user["id"], task.project_id):
                raise HTTPException(
                    status_code=403,
                    detail="Only project managers or superusers can change task priority"
                )

        # Update the task using the task service
        updated_task, error = task_service.update_task(db, task_id, update_data, current_user["id"])
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        if not updated_task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Create activity log for the update
        changes = []
        if "state" in update_data:
            changes.append(f"state to {update_data['state']}")
        if "priority" in update_data:
            changes.append(f"priority to {update_data['priority']}")
        if "assigned_to" in update_data:
            assignee = db.query(User).filter(User.id == update_data["assigned_to"]).first()
            changes.append(f"assignee to {assignee.full_name if assignee else 'unassigned'}")
        
        if changes:
            activity_data = ActivityCreate(
                task_id=task_id,
                project_id=task.project_id,
                user_id=current_user["id"],
                activity_type="task_update",
                description=f"Updated task {', '.join(changes)}"
            )
            activity.create_activity(db, activity_data)

        return updated_task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Delete a specific task."""
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not current_user["is_superuser"] and db_task.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    task_crud.remove(db=db, id=task_id)
    return None

@router.get("/state/{state}", response_model=List[TaskSchema])
async def read_tasks_by_state(
    state: TaskState,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get tasks by state."""
    try:
        tasks = task_crud.get_tasks_by_state(db=db, state=state, skip=skip, limit=limit)
        if not current_user["is_superuser"]:
            tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tasks by state: {str(e)}"
        )

@router.get("/priority/{priority}", response_model=List[TaskSchema])
async def read_tasks_by_priority(
    priority: TaskPriority,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get tasks filtered by priority."""
    try:
        tasks = task_crud.get_tasks_by_priority(
            db=db, priority=priority, skip=skip, limit=limit
        )
        if not current_user["is_superuser"]:
            tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tasks by priority: {str(e)}"
        )

@router.get("/overdue/", response_model=List[TaskSchema])
async def read_overdue_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get all overdue tasks for the current user."""
    try:
        current_date = datetime.utcnow().date()
        tasks = task_crud.get_overdue_tasks(
            db=db, current_date=current_date, skip=skip, limit=limit
        )
        if not current_user["is_superuser"]:
            tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching overdue tasks: {str(e)}"
        )

@router.get("/upcoming/", response_model=List[TaskSchema])
async def read_upcoming_tasks(
    days: int = Query(7, description="Number of days to look ahead"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get tasks due in the next X days."""
    try:
        current_date = datetime.utcnow().date()
        future_date = current_date + timedelta(days=days)
        
        tasks = (
            db.query(TaskModel)
            .filter(
                TaskModel.due_date.between(current_date, future_date),
                TaskModel.status != "done"
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        if not current_user["is_superuser"]:
            tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching upcoming tasks: {str(e)}"
        )

@router.put("/{task_id}/state", response_model=TaskSchema)
async def update_task_state(
    task_id: int,
    state: TaskState = Query(..., description="The new state for the task"),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Update a task's state."""
    try:
        db_task = task_crud.get(db=db, id=task_id)
        if db_task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if not current_user["is_superuser"] and db_task.created_by != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        # Store original state for activity log
        original_state = db_task.state
        
        # Update the task state
        updated_task = task_crud.update_state(db=db, db_obj=db_task, state=state)
        
        # Create base task dictionary for serialization
        task_dict = {
            "id": updated_task.id,
            "name": updated_task.name,
            "description": updated_task.description,
            "priority": updated_task.priority,
            "state": updated_task.state,
            "project_id": updated_task.project_id,
            "stage_id": updated_task.stage_id,
            "assigned_to": updated_task.assigned_to,
            "parent_id": updated_task.parent_id,
            "milestone_id": updated_task.milestone_id,
            "company_id": updated_task.company_id,
            "start_date": updated_task.start_date,
            "end_date": updated_task.end_date,
            "deadline": updated_task.deadline,
            "planned_hours": updated_task.planned_hours,
            "created_by": updated_task.created_by,
            "progress": updated_task.progress if updated_task.progress is not None else 0.0,
            "created_at": updated_task.created_at,
            "updated_at": updated_task.updated_at,
            "date_last_stage_update": updated_task.date_last_stage_update,
            "assignee": None,
            "milestone": None,
            "company": None,
            "depends_on_ids": [],
            "subtask_ids": [],
            "is_active": updated_task.is_active if hasattr(updated_task, 'is_active') else True,
            "completion_status": updated_task.completion_status if hasattr(updated_task, 'completion_status') else CompletionStatus.NOT_COMPLETED
        }
        
        # Handle assignee
        if hasattr(updated_task, 'assignee') and updated_task.assignee:
            task_dict['assignee'] = {
                'id': updated_task.assignee.id,
                'username': updated_task.assignee.username,
                'email': updated_task.assignee.email,
                'full_name': updated_task.assignee.full_name,
                'profile_image_url': getattr(updated_task.assignee, 'profile_image_url', None)
            }
        
        # Handle milestone
        if hasattr(updated_task, 'milestone') and updated_task.milestone:
            task_dict['milestone'] = {
                'id': updated_task.milestone.id,
                'name': updated_task.milestone.name,
                'description': updated_task.milestone.description,
                'due_date': updated_task.milestone.due_date.isoformat() if updated_task.milestone.due_date else None,
                'is_completed': updated_task.milestone.is_completed,
                'is_active': getattr(updated_task.milestone, 'is_active', True)
            }
        
        # Handle company
        if hasattr(updated_task, 'company') and updated_task.company:
            task_dict['company'] = {
                'id': updated_task.company.id,
                'name': updated_task.company.name
            }
        
        # Create activity log for state change
        if original_state != state:
            old_state = original_state.replace("_", " ").title() if original_state else "None"
            new_state = state.replace("_", " ").title()
            description = f"Task status: {old_state} → {new_state}"
            
            activity_data = ActivityCreate(
                activity_type="task_update",
                description=description,
                task_id=task_id,
                project_id=updated_task.project_id,
                user_id=current_user["id"]
            )
            activity.create_activity(db, activity_data)
        
        return TaskSchema.model_validate(task_dict)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating task state: {str(e)}"
        )

@router.get("/created/", response_model=List[TaskSchema])
async def read_created_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get all tasks created by the current user."""
    try:
        tasks = (
            db.query(TaskModel)
            .filter(TaskModel.created_by == current_user["id"])
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching created tasks: {str(e)}"
        )

@router.get("/recent", response_model=List[TaskSchema])
async def read_recent_tasks(
    *,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
    limit: int = 5,
):
    """
    Retrieve recent tasks for the current user.
    """
    try:
        tasks = task_crud.get_recent_tasks(
            db=db, user_id=current_user["id"], limit=limit
        )
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching recent tasks: {str(e)}"
        )

@router.get("/over-budget", response_model=List[TaskSchema])
async def read_over_budget_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get tasks where actual hours exceed estimated hours.
    Useful for project management and resource allocation.
    """
    try:
        tasks = task_crud.get_tasks_over_budget(
            db=db, skip=skip, limit=limit
        )
        
        # Filter tasks for regular users to only see their own or assigned tasks
        if not current_user["is_superuser"]:
            tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching over-budget tasks: {str(e)}"
        )

@router.post("/{task_id}/attachments", response_model=FileAttachmentSchema, status_code=status.HTTP_201_CREATED)
async def upload_task_attachment(
    task_id: int,
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Upload a file attachment to a task."""
    # Verify task exists and user has permission
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Save the file to disk
    unique_filename, file_path, file_size = await file_service.save_file(file, task_id)
    
    # Create file attachment record in database
    file_data = FileAttachmentCreate(
        filename=unique_filename,
        original_filename=file.filename,
        file_size=file_size,
        content_type=file.content_type or "application/octet-stream",
        description=description,
        task_id=task_id
    )
    
    db_file = file_attachment_crud.create_file_attachment(
        db=db, 
        file_data=file_data, 
        user_id=current_user["id"],
        file_path=file_path
    )
    
    return db_file

@router.get("/{task_id}/attachments", response_model=List[FileAttachmentSchema])
async def get_task_attachments(
    task_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get all file attachments for a task."""
    # Verify task exists
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return file_attachment_crud.get_task_attachments(db=db, task_id=task_id, skip=skip, limit=limit)

@router.put("/{task_id}/move-stage")
async def move_task_stage(
    task_id: int,
    new_stage_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Move a task to a different stage"""
    try:
        # Get the task
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Get the new stage
        new_stage = db.query(TaskStage).filter(TaskStage.id == new_stage_id).first()
        if not new_stage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stage not found"
            )
        
        # Check if the new stage belongs to the same project
        if new_stage.project_id != task.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot move task to a stage from a different project"
            )
        
        # Move the task to the new stage
        stage_changed = task.move_to_stage(new_stage_id, db)
        
        if stage_changed:
            db.commit()
            db.refresh(task)
            
            # Ensure proper serialization for the response
            task_dict = {
                "message": "Task stage updated successfully",
                "task": None
            }
            
            if task:
                task_data = TaskSchema.model_validate(task).model_dump()
                # Ensure assignee is a dict if it exists
                if hasattr(task, 'assignee') and task.assignee:
                    task_data['assignee'] = {
                        'id': task.assignee.id,
                        'username': task.assignee.username,
                        'email': task.assignee.email,
                        'full_name': task.assignee.full_name,
                        'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                    }
                task_dict["task"] = task_data
            
            return task_dict
        
        return {"message": "Task is already in this stage"} 
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error moving task to new stage: {str(e)}"
        ) 

@router.post("/{task_id}/tags/{tag_id}", response_model=TaskSchema)
async def add_tag_to_task(
    task_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add a tag to a task.
    """
    # Check if task exists
    task = task_crud.get(db, id=task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check if tag exists
    tag = tag_crud.get(db, id=tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Check if tag is already added
    if tag in task.tags:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag is already added to this task"
        )
    
    # Add tag to task
    task.tags.append(tag)
    db.commit()
    db.refresh(task)
    
    # Log activity
    activity_data = ActivityCreate(
        activity_type="task_update",
        description=f"Added tag: {tag.name}",
        task_id=task_id,
        project_id=task.project_id,
        user_id=current_user["id"]
    )
    activity.create_activity(db, activity_data)
    
    return task

@router.delete("/{task_id}/tags/{tag_id}", response_model=TaskSchema)
async def remove_tag_from_task(
    task_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Remove a tag from a task.
    """
    # Check if task exists
    task = task_crud.get(db, id=task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check if tag exists
    tag = tag_crud.get(db, id=tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Check if tag is added to task
    if tag not in task.tags:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag is not added to this task"
        )
    
    # Remove tag from task
    task.tags.remove(tag)
    db.commit()
    db.refresh(task)
    
    # Log activity
    activity_data = ActivityCreate(
        activity_type="task_update",
        description=f"Removed tag: {tag.name}",
        task_id=task_id,
        project_id=task.project_id,
        user_id=current_user["id"]
    )
    activity.create_activity(db, activity_data)
    
    return task

@router.get("/{task_id}/tags", response_model=List[TagSchema])
async def get_task_tags(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all tags associated with a task.
    """
    task = task_crud.get(db, id=task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return task.tags

@router.put("/{task_id}/tags", response_model=TaskSchema)
async def update_task_tags(
    task_id: int,
    tag_ids: List[int],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update all tags for a task. This will replace existing tags with the new list.
    """
    # Check if task exists
    task = task_crud.get(db, id=task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Verify all tags exist
    tags = []
    for tag_id in tag_ids:
        tag = tag_crud.get(db, id=tag_id)
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag with id {tag_id} not found"
            )
        tags.append(tag)
    
    # Get removed and added tags for activity log
    old_tags = set(task.tags)
    new_tags = set(tags)
    removed_tags = old_tags - new_tags
    added_tags = new_tags - old_tags
    
    # Update task tags
    task.tags = tags
    db.commit()
    db.refresh(task)
    
    # Log activities
    for tag in removed_tags:
        activity_data = ActivityCreate(
            activity_type="task_update",
            description=f"Removed tag: {tag.name}",
            task_id=task_id,
            project_id=task.project_id,
            user_id=current_user["id"]
        )
        activity.create_activity(db, activity_data)
    
    for tag in added_tags:
        activity_data = ActivityCreate(
            activity_type="task_update",
            description=f"Added tag: {tag.name}",
            task_id=task_id,
            project_id=task.project_id,
            user_id=current_user["id"]
        )
        activity.create_activity(db, activity_data)
    
    return task 

@router.post("/{task_id}/follow")
async def follow_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Follow a task."""
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user in task.followers:
        raise HTTPException(status_code=400, detail="Already following this task")

    task.followers.append(user)
    db.commit()

    # Notify task owner
    if task.created_by != current_user["id"]:
        notification_service.create_notification(
            db=db,
            user_id=task.created_by,
            title="New Task Follower",
            content=f"{user.full_name} started following your task '{task.title}'",
            notification_type="task_follow",
            reference_type="task",
            reference_id=task_id
        )

    return {"message": "Successfully followed task"}

@router.delete("/{task_id}/unfollow")
async def unfollow_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Unfollow a task."""
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user not in task.followers:
        raise HTTPException(status_code=400, detail="Not following this task")

    task.followers.remove(user)
    db.commit()

    return {"message": "Successfully unfollowed task"}

@router.get("/{task_id}/time-taken", response_model=Dict[str, Any])
async def get_task_time_taken(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get the time taken by a task from start to completion.
    Returns:
    - time_taken_seconds: Total seconds from start to end
    - time_taken_hours: Time taken in hours
    - time_taken_days: Time taken in days
    - time_taken_human: Human readable format
    - start_date: When the task started
    - end_date: When the task was completed
    - is_completed: Whether the task is completed
    - planned_hours: Originally planned hours
    - time_accuracy: Ratio of actual time to planned time (>1 means took longer than planned)
    """
    try:
        # Get task
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Initialize response
        response = {
            "time_taken_seconds": 0,
            "time_taken_hours": 0,
            "time_taken_days": 0,
            "time_taken_human": "Not started",
            "start_date": task.start_date.replace(tzinfo=timezone.utc) if task.start_date else None,
            "end_date": task.end_date.replace(tzinfo=timezone.utc) if task.end_date else None,
            "is_completed": task.state == "DONE",
            "planned_hours": task.planned_hours or 0,
            "time_accuracy": 0
        }

        # Calculate time taken if task has started
        if task.start_date:
            # Ensure start_date is timezone-aware
            start_time = task.start_date.replace(tzinfo=timezone.utc) if task.start_date.tzinfo is None else task.start_date
            
            # Get end time (either task end_date or current time)
            if task.end_date:
                end_time = task.end_date.replace(tzinfo=timezone.utc) if task.end_date.tzinfo is None else task.end_date
            else:
                end_time = datetime.now(timezone.utc)
            
            # Calculate time delta
            time_delta = end_time - start_time
            
            # Calculate different time formats
            seconds = time_delta.total_seconds()
            hours = seconds / 3600
            days = seconds / (3600 * 24)

            # Update response with calculations
            response.update({
                "time_taken_seconds": round(seconds, 2),
                "time_taken_hours": round(hours, 2),
                "time_taken_days": round(days, 2),
                "time_taken_human": _format_time_delta(time_delta)
            })

            # Calculate time accuracy if planned hours exist
            if task.planned_hours and task.planned_hours > 0:
                response["time_accuracy"] = round(hours / task.planned_hours, 2)

        return response

    except Exception as e:
        import traceback
        traceback.print_exc()  # This will help with debugging
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating task time: {str(e)}"
        )

def _format_time_delta(delta):
    """Format timedelta into human readable string"""
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60

    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    if not parts:
        return "Less than a minute"
    
    return ", ".join(parts)

@router.put("/{task_id}/auto-priority")
async def auto_set_task_priority(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """
    Automatically calculate and set task priority using rules and AI.
    
    The priority is determined by:
    1. First applying rule-based logic for common cases
    2. Using AI for more nuanced decisions when rules are inconclusive
    3. Respecting manual priority if set
    
    Returns both rule-based and AI suggestions along with the final priority.
    """
    try:
        priority_service = PriorityService(db)
        result = await priority_service.calculate_priority(task_id)
        
        # Update task priority if not manually set
        if result["priority_source"] != "MANUAL":
            task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
            if task:
                # Update priority fields
                task.priority = result["final_priority"]
                task.priority_source = result["priority_source"]
                task.priority_reasoning = result.get("reasoning", [])
                
                # Calculate priority score using dedicated scoring service
                scoring_service = PriorityScoringService(db)
                task.priority_score = await scoring_service.calculate_priority_score(task)
                
                db.commit()
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating task priority: {str(e)}"
        )

@router.post("/update-all-priorities")
async def update_all_priorities(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Manually trigger priority updates for all active tasks.
    Only available to superusers.
    """
    if not current_user["is_superuser"]:
        raise HTTPException(
            status_code=403,
            detail="Only superusers can trigger manual priority updates"
        )
        
    try:
        from services.scheduler_service import scheduler_service
        await scheduler_service._update_all_task_priorities()
        return {"message": "Priority update completed successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating priorities: {str(e)}"
        )

@router.put("/{task_id}/calculate-priority-score")
async def calculate_task_priority_score(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Calculate and store a priority score for a task using priority level and complexity.
    This endpoint:
    1. Forces recalculation of the priority score
    2. Updates the score in the database
    3. Returns the new score and its breakdown
    
    Priority score breakdown:
    - Priority Level (80% total):
        * Low = 20%
        * Normal = 40%
        * High = 60%
        * Urgent = 80%
    - Task Complexity (20%)
    
    Returns:
        Dict containing:
        - score: float (0-100)
        - score_breakdown: Dict of component scores
        - explanation: String explaining the score
        - status: Success/error message
    """
    try:
        # Get the task
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        # Check if task is completed or cancelled
        if task.state in ['done', 'cancelled']:
            return {
                "task_id": task.id,
                "score": 0,
                "score_breakdown": {
                    "priority_score": 0,
                    "complexity_score": 0
                },
                "explanation": f"Task is {task.state}, priority calculation not needed",
                "status": f"Task is {task.state}",
                "priority_reasoning": [f"Task is {task.state}"]
            }
            
        # Verify required fields
        missing_fields = []
        if not task.name:
            missing_fields.append("name")
        if not task.priority:
            missing_fields.append("priority level")
            
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields for scoring: {', '.join(missing_fields)}"
            )
            
        # Calculate priority score (80% weight)
        priority_weights = {
            'low': 20,
            'normal': 40,
            'high': 60,
            'urgent': 80
        }
        priority_score = priority_weights.get(task.priority.lower(), 40)  # Default to normal if unknown
        
        # Get task complexity (20% weight)
        try:
            complexity_service = ComplexityService()
            complexity_analysis = await complexity_service.analyze_task_complexity(db, task.id)
            # Convert complexity score to 20% scale
            complexity_score = (complexity_analysis.total_score / 100) * 20
        except Exception as e:
            logger.warning(f"Error calculating complexity for task {task.id}: {str(e)}")
            complexity_score = 10  # Default to medium complexity (50% of 20)
            
        # Calculate total score
        total_score = priority_score + complexity_score
        
        # Generate explanation
        priority_level = task.priority.lower()
        explanation_parts = [
            f"Task priority is {priority_level} ({priority_score}% weight)",
            f"Task complexity score adds {complexity_score:.1f}% weight"
        ]
        
        if hasattr(task, 'dependent_tasks') and task.dependent_tasks:
            explanation_parts.append(f"Task is blocking {len(task.dependent_tasks)} other tasks")
            
        if task.deadline:
            days_to_deadline = (task.deadline - datetime.now(timezone.utc)).days
            if days_to_deadline < 0:
                explanation_parts.append(f"Task is overdue by {abs(days_to_deadline)} days")
            elif days_to_deadline < 7:
                explanation_parts.append(f"Task deadline is in {days_to_deadline} days")
                
        # Update task priority reasoning
        task.priority_reasoning = explanation_parts
        
        # Update the task with new score
        task.priority_score = total_score
        
        # Invalidate any cached priority data
        priority_service = PriorityService(db)
        priority_service.invalidate_cache(task_id)
        
        # Commit changes to database
        db.commit()
        
        # Prepare the response
        response = {
            "task_id": task.id,
            "score": total_score,
            "score_breakdown": {
                "priority_score": priority_score,
                "complexity_score": complexity_score
            },
            "explanation": ". ".join(explanation_parts),
            "status": "Success: Priority score recalculated and updated",
            "priority_reasoning": task.priority_reasoning
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating priority score: {str(e)}"
        )