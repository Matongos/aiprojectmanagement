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

# Helper function to check if a user has assigned tasks in a project
def user_has_project_tasks(db: Session, project_id: int, user_id: int) -> bool:
    """Check if a user has tasks assigned to them in a given project"""
    task_count = db.query(Task).filter(
        Task.project_id == project_id,
        Task.assigned_to == user_id
    ).count()
    return task_count > 0

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
    if current_user.get("is_superuser", False):
        projects = project_crud.get_multi(db, skip=skip, limit=limit)
    else:
        # For regular users, also include projects where they have assigned tasks
        # First get projects they own
        owned_projects = project_crud.get_by_owner(
            db=db, owner_id=current_user["id"], skip=skip, limit=limit
        )
        
        # Get projects with assigned tasks 
        # This query finds all unique project IDs where the user has tasks
        projects_with_tasks_query = db.query(Task.project_id).filter(
            Task.assigned_to == current_user["id"]
        ).distinct()
        
        projects_with_tasks_ids = [p[0] for p in projects_with_tasks_query.all()]
        
        # Get the full project objects for these IDs
        projects_with_tasks = []
        if projects_with_tasks_ids:
            projects_with_tasks = db.query(Project).filter(
                Project.id.in_(projects_with_tasks_ids)
            ).all()
        
        # Combine and deduplicate projects
        all_projects = {project.id: project for project in owned_projects}
        for project in projects_with_tasks:
            if project.id not in all_projects:
                all_projects[project.id] = project
        
        projects = list(all_projects.values())

    # Calculate member count for each project
    for project in projects:
        # Get unique users assigned to tasks in the project
        task_assignees = db.query(Task.assigned_to).filter(
            Task.project_id == project.id,
            Task.assigned_to.isnot(None)
        ).distinct().all()
        
        # Convert to set of unique user IDs, excluding None values
        unique_assignees = {assignee[0] for assignee in task_assignees if assignee[0] is not None}
        
        # Add project creator if not already in the set
        if project.created_by:
            unique_assignees.add(project.created_by)
            
        # Set the member count
        project.member_count = len(unique_assignees)

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
    # For admin users, search all projects
    if current_user.get("is_superuser", False):
        projects = db.query(Project).filter(
            Project.name.ilike(f"%{query}%") | 
            Project.key.ilike(f"%{query}%") | 
            Project.description.ilike(f"%{query}%")
        ).offset(skip).limit(limit).all()
        return projects
    
    # For non-admin users, search only projects they own or have tasks in
    projects = project_crud.search_projects(
        db=db, user_id=current_user["id"], query=query, skip=skip, limit=limit
    )
    
    # Add projects where the user has assigned tasks
    projects_with_tasks_query = db.query(Project).join(Task).filter(
        Task.assigned_to == current_user["id"],
        Project.name.ilike(f"%{query}%") | 
        Project.key.ilike(f"%{query}%") | 
        Project.description.ilike(f"%{query}%")
    ).offset(skip).limit(limit)
    
    projects_with_tasks = projects_with_tasks_query.all()
    
    # Combine and deduplicate projects
    all_projects = {project.id: project for project in projects}
    for project in projects_with_tasks:
        if project.id not in all_projects:
            all_projects[project.id] = project
    
    return list(all_projects.values())

@router.get("/{project_id}", response_model=ProjectSchema)
async def read_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_project = project_crud.get(db=db, id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Superusers can access any project
    if current_user.get("is_superuser", False):
        pass
    # Project creators can access their projects 
    elif db_project.created_by == current_user["id"]:
        pass
    # Users with assigned tasks in the project can access it
    elif user_has_project_tasks(db, project_id, current_user["id"]):
        pass
    else:
        # Otherwise, deny access
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Calculate member count
    task_assignees = db.query(Task.assigned_to).filter(
        Task.project_id == project_id,
        Task.assigned_to.isnot(None)
    ).distinct().all()
    
    # Convert to set of unique user IDs, excluding None values
    unique_assignees = {assignee[0] for assignee in task_assignees if assignee[0] is not None}
    
    # Add project creator if not already in the set
    if db_project.created_by:
        unique_assignees.add(db_project.created_by)
        
    # Set the member count
    db_project.member_count = len(unique_assignees)
    
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
    
    # Only project creators and superusers can update projects
    if not current_user.get("is_superuser", False) and db_project.created_by != current_user["id"]:
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
    
    # Only project creators and superusers can delete projects
    if not current_user.get("is_superuser", False) and db_project.created_by != current_user["id"]:
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
    
    # For admin users, return all projects with the specified status
    if current_user.get("is_superuser", False):
        return projects
    
    # For regular users, return projects they created or have tasks in
    result = []
    for p in projects:
        if p.created_by == current_user["id"] or user_has_project_tasks(db, p.id, current_user["id"]):
            result.append(p)
    
    return result

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
        # For superusers, return recent projects regardless of creator
        if current_user.get("is_superuser", False):
            return db.query(Project).order_by(Project.updated_at.desc()).limit(limit).all()
        
        # Get projects created by the user
        owned_projects = project_crud.get_recent_projects(
            db=db, 
            user_id=current_user["id"], 
            limit=limit
        )
        
        # Get projects with assigned tasks
        projects_with_tasks_query = db.query(Project).join(Task).filter(
            Task.assigned_to == current_user["id"]
        ).order_by(Project.updated_at.desc()).limit(limit)
        
        projects_with_tasks = projects_with_tasks_query.all()
        
        # Combine and deduplicate projects, keeping the most recent ones up to the limit
        all_projects = {project.id: project for project in owned_projects}
        for project in projects_with_tasks:
            if project.id not in all_projects and len(all_projects) < limit:
                all_projects[project.id] = project
        
        result = list(all_projects.values())
        # Sort by updated_at in descending order
        result.sort(key=lambda x: x.updated_at, reverse=True)
        # Limit to the requested number
        return result[:limit]
        
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
    
    # Only project creators and superusers can add stages
    if not current_user.get("is_superuser", False) and db_project.created_by != current_user["id"]:
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
    
    # Check user access permissions
    has_access = (
        current_user.get("is_superuser", False) or 
        db_project.created_by == current_user["id"] or
        user_has_project_tasks(db, project_id, current_user["id"])
    )
    
    if not has_access:
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
    
    # Only project creators and superusers can delete stages
    if not current_user.get("is_superuser", False) and db_project.created_by != current_user["id"]:
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