from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from models.task import Task, TaskStatus, TaskPriority
from schemas.task import TaskCreate, TaskUpdate, Task as TaskSchema
from crud import task as task_crud
from database import get_db
from routers.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskSchema)
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new task with the current user as creator."""
    return task_crud.create_with_creator(db=db, obj_in=task, creator_id=current_user["id"])

@router.get("/", response_model=List[TaskSchema])
async def read_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tasks assigned to the current user."""
    tasks = task_crud.get_by_assignee(
        db=db, assignee_id=current_user["id"], skip=skip, limit=limit
    )
    return tasks

@router.get("/project/{project_id}", response_model=List[TaskSchema])
async def read_project_tasks(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
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
    current_user: dict = Depends(get_current_user)
):
    """Get a specific task by ID."""
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.creator_id != current_user["id"] and db_task.assignee_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db_task

@router.put("/{task_id}", response_model=TaskSchema)
async def update_task(
    task_id: int,
    task: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a specific task."""
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.creator_id != current_user["id"] and db_task.assignee_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return task_crud.update(db=db, db_obj=db_task, obj_in=task)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a specific task."""
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.creator_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    task_crud.remove(db=db, id=task_id)
    return None

@router.get("/status/{status}", response_model=List[TaskSchema])
async def read_tasks_by_status(
    status: TaskStatus,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tasks filtered by status."""
    tasks = task_crud.get_by_status(
        db=db, status=status, skip=skip, limit=limit
    )
    return [t for t in tasks if t.creator_id == current_user["id"] or t.assignee_id == current_user["id"]]

@router.get("/priority/{priority}", response_model=List[TaskSchema])
async def read_tasks_by_priority(
    priority: TaskPriority,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tasks filtered by priority."""
    tasks = task_crud.get_tasks_by_priority(
        db=db, priority=priority, skip=skip, limit=limit
    )
    return [t for t in tasks if t.creator_id == current_user["id"] or t.assignee_id == current_user["id"]]

@router.get("/overdue/", response_model=List[TaskSchema])
async def read_overdue_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all overdue tasks for the current user."""
    current_date = datetime.utcnow()
    tasks = task_crud.get_overdue_tasks(
        db=db, current_date=current_date, skip=skip, limit=limit
    )
    return [t for t in tasks if t.creator_id == current_user["id"] or t.assignee_id == current_user["id"]]

@router.get("/upcoming/", response_model=List[TaskSchema])
async def read_upcoming_tasks(
    days: int = Query(7, description="Number of days to look ahead"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tasks due in the next X days."""
    current_date = datetime.utcnow()
    future_date = current_date + timedelta(days=days)
    
    tasks = (
        db.query(Task)
        .filter(
            Task.due_date.between(current_date, future_date),
            Task.status != TaskStatus.DONE
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return [t for t in tasks if t.creator_id == current_user["id"] or t.assignee_id == current_user["id"]]

@router.put("/{task_id}/status", response_model=TaskSchema)
async def update_task_status(
    task_id: int,
    status: TaskStatus,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update just the status of a task."""
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.creator_id != current_user["id"] and db_task.assignee_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return task_crud.update(db=db, db_obj=db_task, obj_in={"status": status})

@router.get("/created/", response_model=List[TaskSchema])
async def read_created_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all tasks created by the current user."""
    tasks = (
        db.query(Task)
        .filter(Task.creator_id == current_user["id"])
        .offset(skip)
        .limit(limit)
        .all()
    )
    return tasks 