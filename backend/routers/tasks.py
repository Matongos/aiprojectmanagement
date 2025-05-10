from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from models.task import Task
from models.task_stage import TaskStage
from schemas.task import TaskCreate, TaskUpdate, Task as TaskSchema, TaskState, TaskPriority
from schemas.file_attachment import FileAttachment as FileAttachmentSchema, FileAttachmentCreate
from crud import task as task_crud
from crud import file_attachment as file_attachment_crud
from database import get_db
from routers.auth import get_current_user
from schemas.user import User
from services.file_service import FileService
from services.notification_service import NotificationService
from services.task_service import TaskService
from models.projects import Project

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

@router.post("/", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new task with required fields: name, project_id, and stage_id."""
    try:
        # Convert 0 values to None for foreign keys
        task_data = task.model_dump()
        if task_data.get('assigned_to', 0) == 0:
            task_data['assigned_to'] = None
        if task_data.get('parent_id', 0) == 0:
            task_data['parent_id'] = None

        # Validate that the project exists
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {task.project_id} not found"
            )

        # Validate that the stage exists and belongs to the project
        stage = db.query(TaskStage).filter(
            TaskStage.id == task.stage_id,
            TaskStage.project_id == task.project_id
        ).first()
        
        if not stage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stage with ID {task.stage_id} not found in project {task.project_id}"
            )

        # Create the task with modified data
        created_task, error = task_service.create_task(db, task_data, current_user["id"])
        
        if error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
        
        return created_task

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}"
        )

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
    if project_id:
        tasks = task_crud.get_project_tasks(db, project_id, skip, limit)
    elif stage_id:
        tasks = task_crud.get_tasks_by_stage(db, stage_id, skip, limit)
    elif search:
        tasks = task_crud.search_tasks(db, search_term=search, skip=skip, limit=limit)
    else:
        tasks = task_crud.get_user_tasks(db, current_user["id"], skip, limit)
    if not current_user["is_superuser"]:
        tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
    return tasks

@router.get("/my", response_model=List[TaskSchema])
async def read_my_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tasks assigned to or created by the current user"""
    return task_crud.get_user_tasks(db, current_user["id"], skip, limit)

@router.get("/{task_id}", response_model=TaskSchema)
async def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get a specific task by ID."""
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not current_user["is_superuser"] and db_task.assigned_to != current_user["id"] and db_task.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Create base task dictionary
    task_dict = {
        "id": db_task.id,
        "name": db_task.name,
        "description": db_task.description,
        "priority": db_task.priority,
        "state": db_task.state,
        "project_id": db_task.project_id,
        "stage_id": db_task.stage_id,
        "assigned_to": db_task.assigned_to,
        "milestone_id": db_task.milestone_id,
        "milestone": db_task.milestone,
        "deadline": db_task.deadline,
        "progress": db_task.progress if db_task.progress is not None else 0.0,
        "created_at": db_task.created_at,
        "updated_at": db_task.updated_at,
        "created_by": db_task.created_by  # Always include created_by
    }
    
    # Add assignee details if present
    if db_task.assignee:
        task_dict["assignee"] = {
            "id": db_task.assignee.id,
            "username": db_task.assignee.username,
            "email": db_task.assignee.email,
            "full_name": db_task.assignee.full_name,
            "profile_image_url": db_task.assignee.profile_image_url
        }
    
    return TaskSchema(**task_dict)

@router.put("/{task_id}", response_model=TaskSchema)
async def update_task(
    task_id: int,
    task: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Update a specific task."""
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not current_user["is_superuser"] and db_task.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Check if assignee has changed
    original_assignee_id = db_task.assigned_to
    
    # Update the task
    updated_task = task_crud.update(db=db, db_obj=db_task, obj_in=task)
    
    # Process mentions in updated description 
    if task.description:
        user_service.process_user_mentions(
            db, 
            task.description, 
            current_user["id"], 
            "task", 
            task_id,
            notification_service
        )
    
    # Send notifications for assignment changes
    if task.assigned_to is not None and task.assigned_to != original_assignee_id:
        # Notify new assignee
        notification_data = {
            "user_id": task.assigned_to,
            "title": "Task Assignment",
            "content": f"You have been assigned to the task: {updated_task.name}",
            "type": "task_assignment",
            "reference_type": "task",
            "reference_id": task_id,
            "is_read": False
        }
        notification_service.create_notification(db, notification_data)
    
    # Send notifications if status has changed
    if task.status is not None and task.status != db_task.status:
        # Notify creator and assignee (if different from current user and creator)
        users_to_notify = set()
        if db_task.created_by and db_task.created_by != current_user["id"]:
            users_to_notify.add(db_task.created_by)
        if db_task.assigned_to and db_task.assigned_to != current_user["id"] and db_task.assigned_to != db_task.created_by:
            users_to_notify.add(db_task.assigned_to)
            
        if users_to_notify:
            # Notify all users in users_to_notify
            for user_id in users_to_notify:
                notification_data = {
                    "user_id": user_id,
                    "title": "Task Status Changed",
                    "content": f"Task '{updated_task.name}' status changed to {task.status}",
                    "type": "task_status",
                    "reference_type": "task",
                    "reference_id": task_id,
                    "is_read": False
                }
                notification_service.create_notification(db, notification_data)
    
    return updated_task

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
    tasks = task_crud.get_tasks_by_state(db=db, state=state, skip=skip, limit=limit)
    if not current_user["is_superuser"]:
        tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
    return tasks

@router.get("/priority/{priority}", response_model=List[TaskSchema])
async def read_tasks_by_priority(
    priority: TaskPriority,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get tasks filtered by priority."""
    tasks = task_crud.get_tasks_by_priority(
        db=db, priority=priority, skip=skip, limit=limit
    )
    if not current_user["is_superuser"]:
        tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
    return tasks

@router.get("/overdue/", response_model=List[TaskSchema])
async def read_overdue_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get all overdue tasks for the current user."""
    current_date = datetime.utcnow().date()
    tasks = task_crud.get_overdue_tasks(
        db=db, current_date=current_date, skip=skip, limit=limit
    )
    if not current_user["is_superuser"]:
        tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
    return tasks

@router.get("/upcoming/", response_model=List[TaskSchema])
async def read_upcoming_tasks(
    days: int = Query(7, description="Number of days to look ahead"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get tasks due in the next X days."""
    current_date = datetime.utcnow().date()
    future_date = current_date + timedelta(days=days)
    
    tasks = (
        db.query(Task)
        .filter(
            Task.due_date.between(current_date, future_date),
            Task.status != "done"
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    if not current_user["is_superuser"]:
        tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
    
    return tasks

@router.put("/{task_id}/state", response_model=TaskSchema)
async def update_task_state(
    task_id: int,
    state: TaskState,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Update a task's state."""
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not current_user["is_superuser"] and db_task.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    updated_task = task_crud.update_state(db=db, db_obj=db_task, state=state)
    return updated_task

@router.get("/created/", response_model=List[TaskSchema])
async def read_created_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get all tasks created by the current user."""
    tasks = (
        db.query(Task)
        .filter(Task.created_by == current_user["id"])
        .offset(skip)
        .limit(limit)
        .all()
    )
    return tasks

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
    tasks = task_crud.get_recent_tasks(
        db=db, user_id=current_user["id"], limit=limit
    )
    return tasks

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
    tasks = task_crud.get_tasks_over_budget(
        db=db, skip=skip, limit=limit
    )
    
    # Filter tasks for regular users to only see their own or assigned tasks
    if not current_user["is_superuser"]:
        tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
    
    return tasks

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
    
    # Get the task
    task = db.query(Task).filter(Task.id == task_id).first()
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
        return {"message": "Task stage updated successfully"}
    
    return {"message": "Task is already in this stage"} 