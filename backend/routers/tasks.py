from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models.task import Task, TaskStatus
from schemas.task import TaskCreate, TaskUpdate, Task as TaskSchema
from crud import task as task_crud
from database import get_db
from routers.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskSchema)
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return task_crud.create_with_creator(db=db, obj_in=task, creator_id=current_user.id)

@router.get("/", response_model=List[TaskSchema])
async def read_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tasks = task_crud.get_by_assignee(
        db=db, assignee_id=current_user.id, skip=skip, limit=limit
    )
    return tasks

@router.get("/project/{project_id}", response_model=List[TaskSchema])
async def read_project_tasks(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tasks = task_crud.get_by_project(
        db=db, project_id=project_id, skip=skip, limit=limit
    )
    return tasks

@router.get("/{task_id}", response_model=TaskSchema)
async def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.creator_id != current_user.id and db_task.assignee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db_task

@router.put("/{task_id}", response_model=TaskSchema)
async def update_task(
    task_id: int,
    task: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.creator_id != current_user.id and db_task.assignee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return task_crud.update(db=db, db_obj=db_task, obj_in=task)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    task_crud.remove(db=db, id=task_id)
    return None

@router.get("/status/{status}", response_model=List[TaskSchema])
async def read_tasks_by_status(
    status: TaskStatus,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tasks = task_crud.get_by_status(
        db=db, status=status, skip=skip, limit=limit
    )
    return [t for t in tasks if t.creator_id == current_user.id or t.assignee_id == current_user.id] 