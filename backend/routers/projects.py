from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from models.projects import Project, ProjectMember
from models.task_stage import TaskStage
from schemas.project import (
    ProjectCreate, 
    ProjectUpdate, 
    Project as ProjectSchema
)
from schemas.task import (
    TaskStage as TaskStageSchema,
    TaskStageCreate,
    TaskStageWithTasks
)
from crud import project as project_crud
from crud.project import project_stage
from database import get_db
from routers.auth import get_current_user, User
from models.task import Task

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=ProjectSchema)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return project_crud.create_with_owner(db=db, obj_in=project, owner_id=current_user["id"])

@router.get("/", response_model=List[ProjectSchema])
async def read_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    projects = project_crud.get_by_owner(
        db=db, owner_id=current_user["id"], skip=skip, limit=limit
    )
    return projects

@router.get("/search/", response_model=List[ProjectSchema])
async def search_projects(
    query: str = Query(..., description="Search query for projects"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Search for projects by name, key, or description.
    """
    projects = project_crud.search_projects(
        db=db, user_id=current_user["id"], query=query, skip=skip, limit=limit
    )
    return projects

@router.get("/{project_id}", response_model=ProjectSchema)
async def read_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_project = project_crud.get(db=db, id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if db_project.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db_project

@router.put("/{project_id}", response_model=ProjectSchema)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a project's details"""
    # Check if project exists and user has access
    db_project = project_crud.get(db=db, id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    if db_project.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Update the project
    return project_crud.update(db=db, db_obj=db_project, obj_in=project_update)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_project = project_crud.get(db=db, id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if db_project.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    project_crud.remove(db=db, id=project_id)
    return None

@router.get("/status/{status}", response_model=List[ProjectSchema])
async def read_projects_by_status(
    status: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    projects = project_crud.get_by_status(
        db=db, status=status, skip=skip, limit=limit
    )
    return [p for p in projects if p.created_by == current_user["id"]]

@router.get("/recent/", response_model=List[ProjectSchema])
async def read_recent_projects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    limit: int = Query(5, ge=1, le=50, description="Number of recent projects to return")
) -> List[ProjectSchema]:
    """
    Retrieve recent projects for the current user.
    Limit parameter is validated to be between 1 and 50.
    """
    if not current_user or "id" not in current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    try:
        projects = project_crud.get_recent_projects(
            db=db, 
            user_id=current_user["id"], 
            limit=limit
        )
        return projects
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{project_id}/stages", response_model=TaskStageSchema)
async def create_project_stage(
    project_id: int,
    stage: TaskStageCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new stage for a project"""
    # Check if project exists and user has access
    db_project = project_crud.get(db=db, id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    if db_project.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Create the stage
    return project_stage.create_stage(db=db, obj_in=stage)

@router.get("/{project_id}/stages", response_model=List[TaskStageWithTasks])
async def get_project_stages(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all stages for a project with their tasks"""
    # Check if project exists and user has access
    db_project = project_crud.get(db=db, id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    if db_project.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Get stages with tasks
    stages = db.query(TaskStage).filter(TaskStage.project_id == project_id).order_by(TaskStage.sequence).all()
    
    # For each stage, load its tasks
    for stage in stages:
        stage.tasks = db.query(Task).filter(Task.stage_id == stage.id).all()
    
    return stages

@router.delete("/{project_id}/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_stage(
    project_id: int,
    stage_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a stage from a project"""
    # Check if project exists and user has access
    db_project = project_crud.get(db=db, id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    if db_project.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Check if stage exists and belongs to the project
    db_stage = project_stage.get(db=db, id=stage_id)
    if not db_stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    if db_stage.project_id != project_id:
        raise HTTPException(status_code=400, detail="Stage does not belong to this project")
    
    # Delete the stage
    project_stage.remove(db=db, id=stage_id)
    return None

@router.get("/tags", response_model=List[str])
async def get_project_tags(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all unique project tags"""
    return project_crud.get_all_tags(db)

@router.get("/{project_id}/members")
async def get_project_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all users that can be assigned to tasks"""
    # Check if project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all active users
    users = db.query(User).filter(User.is_active == True).all()
    
    # Return user data in the format needed by the frontend
    return [
        {
            "id": user.id,
            "name": user.full_name or user.username,
            "profile_image_url": user.profile_image_url
        }
        for user in users
    ] 