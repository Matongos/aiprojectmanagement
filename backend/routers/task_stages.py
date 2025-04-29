from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas.task_stage import TaskStage, TaskStageCreate, TaskStageUpdate
from crud.task_stage import task_stage
from routers.auth import get_current_user

router = APIRouter(prefix="/task-stages", tags=["task-stages"])

@router.post("/", response_model=TaskStage)
async def create_task_stage(
    stage: TaskStageCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new task stage."""
    return task_stage.create_stage(db=db, obj_in=stage)

@router.get("/project/{project_id}", response_model=List[TaskStage])
async def get_project_task_stages(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all task stages for a project."""
    return task_stage.get_project_stages(db=db, project_id=project_id)

@router.put("/{stage_id}", response_model=TaskStage)
async def update_task_stage(
    stage_id: int,
    stage_update: TaskStageUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a task stage."""
    db_stage = task_stage.get(db=db, id=stage_id)
    if not db_stage:
        raise HTTPException(status_code=404, detail="Task stage not found")
    return task_stage.update(db=db, db_obj=db_stage, obj_in=stage_update)

@router.put("/{stage_id}/sequence", response_model=TaskStage)
async def update_stage_sequence(
    stage_id: int,
    new_sequence: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update the sequence order of a task stage."""
    updated_stage = task_stage.update_sequence(
        db=db,
        stage_id=stage_id,
        new_sequence=new_sequence,
        project_id=project_id
    )
    if not updated_stage:
        raise HTTPException(status_code=404, detail="Task stage not found")
    return updated_stage

@router.delete("/{stage_id}")
async def delete_task_stage(
    stage_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a task stage."""
    db_stage = task_stage.get(db=db, id=stage_id)
    if not db_stage:
        raise HTTPException(status_code=404, detail="Task stage not found")
    task_stage.remove(db=db, id=stage_id)
    return {"message": "Task stage deleted successfully"} 