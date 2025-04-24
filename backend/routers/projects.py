from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from models.projects import Project
from schemas.project import ProjectCreate, ProjectUpdate, Project as ProjectSchema
from crud import project as project_crud
from database import get_db
from routers.auth import get_current_user
from schemas.user import User

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
    project: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_project = project_crud.get(db=db, id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if db_project.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return project_crud.update(db=db, db_obj=db_project, obj_in=project)

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
def read_recent_projects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    limit: int = Query(5, description="Number of recent projects to return")
) -> Any:
    """
    Retrieve recent projects for the current user.
    """
    projects = project_crud.get_recent_projects(db=db, user_id=current_user["id"], limit=limit)
    return projects 