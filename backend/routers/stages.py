from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from database import get_db
from models.task_stage import TaskStage
from models.task import Task
from schemas.task_stage import TaskStageCreate, TaskStageUpdate, TaskStageWithTasks
from crud import task_stage as stage_crud
from routers.auth import get_current_user

router = APIRouter(prefix="/stages", tags=["stages"])

@router.post("/", response_model=TaskStageWithTasks)
async def create_stage(
    stage: TaskStageCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new task stage"""
    return stage_crud.create_stage(db=db, obj_in=stage)

@router.get("/project/{project_id}", response_model=List[TaskStageWithTasks])
async def read_project_stages(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all stages for a project"""
    return stage_crud.get_project_stages(db=db, project_id=project_id)

@router.get("/{stage_id}", response_model=TaskStageWithTasks)
async def read_stage(
    stage_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific stage by ID"""
    stage = stage_crud.get_stage(db, stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage

@router.put("/{stage_id}", response_model=TaskStageWithTasks)
async def update_stage(
    stage_id: int,
    stage_update: TaskStageUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a stage"""
    stage = stage_crud.get_stage(db, stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage_crud.update_stage(db=db, db_obj=stage, obj_in=stage_update)

@router.delete("/{stage_id}")
async def delete_stage(
    stage_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a stage"""
    stage = stage_crud.get_stage(db, stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    stage_crud.delete_stage(db=db, stage_id=stage_id)
    return {"status": "success"}

@router.post("/project/{project_id}/reorder")
async def reorder_stages(
    project_id: int,
    stage_order: List[int],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Reorder stages in a project"""
    stages = stage_crud.reorder_stages(db, project_id, stage_order)
    return {"status": "success", "stages": stages}

@router.post("/{stage_id}/tasks/{task_id}")
async def move_task_to_stage(
    stage_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Move a task to a specific stage"""
    # Get task and verify it exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Get stage and verify it exists
    stage = db.query(TaskStage).filter(TaskStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
        
    # Verify stage belongs to the same project as task
    if stage.project_id != task.project_id:
        raise HTTPException(
            status_code=400, 
            detail="Stage does not belong to the task's project"
        )
    
    # Move task to new stage
    changed = task.move_to_stage(stage_id, db)
    db.commit()
    
    return {"success": True, "stage_changed": changed}

@router.post("/tasks/{task_id}/next")
async def move_task_to_next_stage(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Move a task to the next stage in sequence"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    next_stage = task.get_next_stage(db)
    if not next_stage:
        raise HTTPException(status_code=400, detail="No next stage available")
    
    changed = task.move_to_stage(next_stage.id, db)
    db.commit()
    
    return {"success": True, "stage_changed": changed}

@router.post("/tasks/{task_id}/previous")
async def move_task_to_previous_stage(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Move a task to the previous stage in sequence"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    prev_stage = task.get_previous_stage(db)
    if not prev_stage:
        raise HTTPException(status_code=400, detail="No previous stage available")
    
    changed = task.move_to_stage(prev_stage.id, db)
    db.commit()
    
    return {"success": True, "stage_changed": changed}

@router.get("/{stage_id}/tasks")
async def get_stage_tasks(
    stage_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all tasks in a specific stage"""
    # Verify stage exists
    stage = db.query(TaskStage).filter(TaskStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    tasks = (
        db.query(Task)
        .filter(Task.stage_id == stage_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return tasks 