from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from models.tasks import Task
from schemas.task import TaskCreate, TaskUpdate, Task as TaskSchema, TaskStatus, TaskPriority
from schemas.file_attachment import FileAttachment as FileAttachmentSchema, FileAttachmentCreate
from crud import task as task_crud
from crud import file_attachment as file_attachment_crud
from database import get_db
from routers.auth import get_current_user
from schemas.user import User
from services.file_service import FileService
from services.notification_service import NotificationService
from services import task_service, user_service

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)

# File attachment endpoints
file_service = FileService()

notification_service = NotificationService()

@router.post("/", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    created_task, error = task_service.create_task(db, task.dict(), current_user.id)
    
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    
    # Process mentions in task description and notify mentioned users
    if task.description:
        user_service.process_user_mentions(
            db, 
            task.description, 
            current_user.id, 
            "task", 
            created_task["id"],
            notification_service
        )
    
    # Send notification to assigned user if different from creator
    if task.assigned_to and task.assigned_to != current_user.id:
        assigned_user = user_service.get_user_by_id(db, task.assigned_to)
        if assigned_user:
            notification_data = {
                "user_id": task.assigned_to,
                "title": "New Task Assignment",
                "content": f"You have been assigned to the task: {task.title}",
                "type": "task_assignment",
                "reference_type": "task",
                "reference_id": created_task["id"],
                "is_read": False
            }
            notification_service.create_notification(db, notification_data)
    
    return created_task

@router.get("/", response_model=List[TaskSchema])
async def read_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get tasks assigned to the current user."""
    if not current_user["is_superuser"]:
        tasks = task_crud.get_by_assignee(
            db=db, assignee_id=current_user["id"], skip=skip, limit=limit
        )
    else:
        tasks = task_crud.get_multi(db=db, skip=skip, limit=limit)
    return tasks

@router.get("/project/{project_id}", response_model=List[TaskSchema])
async def read_project_tasks(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get all tasks for a specific project."""
    tasks = task_crud.get_by_project(
        db=db, project_id=project_id, skip=skip, limit=limit
    )
    return tasks

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
    if not current_user["is_superuser"] and db_task.assignee_id != current_user["id"] and db_task.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db_task

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
    original_assignee_id = db_task.assignee_id
    
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
    if task.assignee_id is not None and task.assignee_id != original_assignee_id:
        # Notify new assignee
        notification_data = {
            "user_id": task.assignee_id,
            "title": "Task Assignment",
            "content": f"You have been assigned to the task: {updated_task.title}",
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
        if db_task.assignee_id and db_task.assignee_id != current_user["id"] and db_task.assignee_id != db_task.created_by:
            users_to_notify.add(db_task.assignee_id)
            
        if users_to_notify:
            # Notify all users in users_to_notify
            for user_id in users_to_notify:
                notification_data = {
                    "user_id": user_id,
                    "title": "Task Status Changed",
                    "content": f"Task '{updated_task.title}' status changed to {task.status}",
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

@router.get("/status/{status}", response_model=List[TaskSchema])
async def read_tasks_by_status(
    status: TaskStatus,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get tasks filtered by status."""
    tasks = task_crud.get_by_status(
        db=db, status=status, skip=skip, limit=limit
    )
    if not current_user["is_superuser"]:
        tasks = [t for t in tasks if t.assignee_id == current_user["id"] or t.created_by == current_user["id"]]
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
        tasks = [t for t in tasks if t.assignee_id == current_user["id"] or t.created_by == current_user["id"]]
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
        tasks = [t for t in tasks if t.assignee_id == current_user["id"] or t.created_by == current_user["id"]]
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
        tasks = [t for t in tasks if t.assignee_id == current_user["id"] or t.created_by == current_user["id"]]
    
    return tasks

@router.put("/{task_id}/status", response_model=TaskSchema)
async def update_task_status(
    task_id: int,
    status: TaskStatus,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Update just the status of a task."""
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not current_user["is_superuser"] and db_task.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return task_crud.update(db=db, db_obj=db_task, obj_in={"status": status})

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
        tasks = [t for t in tasks if t.assignee_id == current_user["id"] or t.created_by == current_user["id"]]
    
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