from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from models.project import Project as ProjectModel, ProjectMember, ProjectRole
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
from schemas.tag import Tag as TagSchema
from crud.tag import tag as tag_crud
from crud import activity
from schemas.activity import ActivityCreate
from services.notification_service import NotificationService
from services.permission_service import PermissionService
from pydantic import BaseModel, validator, conint
from enum import Enum

# Add new schema for member role update
class ProjectMemberUpdate(BaseModel):
    role: conint(ge=1, le=3)  # Constrained integer between 1 and 3

    class Config:
        json_schema_extra = {
            "example": {
                "role": 1  # 1=manager, 2=member, 3=viewer
            }
        }

    @validator('role')
    def validate_role(cls, v):
        if v not in [1, 2, 3]:
            raise ValueError("Role must be 1 (manager), 2 (member), or 3 (viewer)")
        return ProjectRole(v)  # Convert to enum

router = APIRouter(prefix="/projects", tags=["projects"])

notification_service = NotificationService()
permission_service = PermissionService()

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
    """Get all projects with access information."""
    # Get all projects
    projects = project_crud.get_multi(db, skip=skip, limit=limit)
    
    # Get projects with assigned tasks for the current user
    projects_with_tasks_query = db.query(Task.project_id).filter(
        Task.assigned_to == current_user["id"]
    ).distinct()
    
    projects_with_tasks_ids = set(p[0] for p in projects_with_tasks_query.all())
    
    # For each project, calculate member count and add access information
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
        
        # Add access information
        project.has_user_tasks = project.id in projects_with_tasks_ids
        project.has_access = (
            current_user.get("is_superuser", False) or  # Admin access
            project.created_by == current_user["id"] or  # Creator access
            project.id in projects_with_tasks_ids  # Has assigned tasks
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
    # For admin users, search all projects
    if current_user.get("is_superuser", False):
        projects = db.query(ProjectModel).filter(
            ProjectModel.name.ilike(f"%{query}%") | 
            ProjectModel.key.ilike(f"%{query}%") | 
            ProjectModel.description.ilike(f"%{query}%")
        ).offset(skip).limit(limit).all()
        return projects
    
    # For non-admin users, search only projects they own or have tasks in
    projects = project_crud.search_projects(
        db=db, user_id=current_user["id"], query=query, skip=skip, limit=limit
    )
    
    # Add projects where the user has assigned tasks
    projects_with_tasks_query = db.query(ProjectModel).join(Task).filter(
        Task.assigned_to == current_user["id"],
        ProjectModel.name.ilike(f"%{query}%") | 
        ProjectModel.key.ilike(f"%{query}%") | 
        ProjectModel.description.ilike(f"%{query}%")
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
            return db.query(ProjectModel).order_by(ProjectModel.updated_at.desc()).limit(limit).all()
        
        # Get projects created by the user
        owned_projects = project_crud.get_recent_projects(
            db=db, 
            user_id=current_user["id"], 
            limit=limit
        )
        
        # Get projects with assigned tasks
        projects_with_tasks_query = db.query(ProjectModel).join(Task).filter(
            Task.assigned_to == current_user["id"]
        ).order_by(ProjectModel.updated_at.desc()).limit(limit)
        
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

@router.get("/{project_id}/members", response_model=List[dict])
async def get_project_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all project members with their roles"""
    # Check if project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if user has access to view members
    if not permission_service.can_modify_project(db, current_user["id"], project_id):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Get all project members with their roles
    project_members = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id
    ).all()

    # Get all users that are members
    member_users = db.query(User).filter(
        User.id.in_([pm.user_id for pm in project_members])
    ).all()

    # Create a mapping of user_id to user details
    user_map = {user.id: user for user in member_users}

    # Return member data with roles
    return [
        {
            "id": pm.user_id,
            "name": user_map[pm.user_id].full_name or user_map[pm.user_id].username,
            "profile_image_url": user_map[pm.user_id].profile_image_url,
            "role": pm.role.value
        }
        for pm in project_members
        if pm.user_id in user_map
    ]

@router.put("/{project_id}/members/{user_id}/role", response_model=dict)
async def update_project_member_role(
    project_id: int,
    user_id: int,
    member_update: ProjectMemberUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a project member's role.
    
    Available roles:
    - manager: Full project management permissions
    - member: Regular project member permissions
    - viewer: Read-only access
    
    Example request body:
    ```json
    {
        "role": 1
    }
    ```
    """
    # Check if project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Only project owner or superuser can update roles
    if not (current_user.get("is_superuser", False) or project.owner_id == current_user["id"]):
        raise HTTPException(status_code=403, detail="Only project owner or superuser can update member roles")

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get or create project member
    project_member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()

    if not project_member:
        project_member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=member_update.role  # This is already an integer from the schema validation
        )
        db.add(project_member)
    else:
        project_member.role = member_update.role  # This is already an integer from the schema validation

    db.commit()
    db.refresh(project_member)

    # Create activity log
    activity_data = ActivityCreate(
        project_id=project_id,
        user_id=current_user["id"],
        activity_type="member_role_update",
        description=f"Updated role of {user.full_name or user.username} to {ProjectRole(member_update.role).name.lower()}"
    )
    activity.create_activity(db, activity_data)

    # Return updated member data
    return {
        "id": user.id,
        "name": user.full_name or user.username,
        "profile_image_url": user.profile_image_url,
        "role": project_member.role.value
    }

@router.post("/{project_id}/members/{user_id}", response_model=dict)
async def add_project_member(
    project_id: int,
    user_id: int,
    member_update: ProjectMemberUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add a new member to the project with a specific role.
    
    Available roles:
    - manager: Full project management permissions
    - member: Regular project member permissions
    - viewer: Read-only access
    
    Example request body:
    ```json
    {
        "role": 1
    }
    ```
    """
    # Check if project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Only project owner or superuser can add members
    if not (current_user.get("is_superuser", False) or project.owner_id == current_user["id"]):
        raise HTTPException(status_code=403, detail="Only project owner or superuser can add members")

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user is already a member
    existing_member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()

    if existing_member:
        raise HTTPException(status_code=400, detail="User is already a project member")

    # Create new project member
    project_member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=member_update.role  # This is already an integer from the schema validation
    )
    db.add(project_member)
    db.commit()
    db.refresh(project_member)

    # Create activity log
    activity_data = ActivityCreate(
        project_id=project_id,
        user_id=current_user["id"],
        activity_type="member_added",
        description=f"Added {user.full_name or user.username} as {ProjectRole(member_update.role).name.lower()}"
    )
    activity.create_activity(db, activity_data)

    # Return member data
    return {
        "id": user.id,
        "name": user.full_name or user.username,
        "profile_image_url": user.profile_image_url,
        "role": project_member.role.value
    }

@router.delete("/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove a member from the project"""
    # Check if project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Only project owner or superuser can remove members
    if not (current_user.get("is_superuser", False) or project.owner_id == current_user["id"]):
        raise HTTPException(status_code=403, detail="Only project owner or superuser can remove members")

    # Check if user exists and is a member
    project_member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()

    if not project_member:
        raise HTTPException(status_code=404, detail="User is not a project member")

    # Cannot remove the project owner
    if project.owner_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove the project owner")

    # Get user info for activity log
    user = db.query(User).filter(User.id == user_id).first()

    # Remove member
    db.delete(project_member)
    db.commit()

    # Create activity log
    activity_data = ActivityCreate(
        project_id=project_id,
        user_id=current_user["id"],
        activity_type="member_removed",
        description=f"Removed {user.full_name or user.username} from project"
    )
    activity.create_activity(db, activity_data)

    return {"status": "success", "message": "Member removed successfully"}

@router.post("/{project_id}/tags/{tag_id}", response_model=ProjectSchema)
async def add_tag_to_project(
    project_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add a tag to a project.
    """
    # Check if project exists
    project = project_crud.get(db, id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if tag exists
    tag = tag_crud.get(db, id=tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Check if tag is already added
    if tag in project.tags:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag is already added to this project"
        )
    
    # Add tag to project
    project.tags.append(tag)
    db.commit()
    db.refresh(project)
    
    # Log activity
    activity.create(
        db,
        ActivityCreate(
            activity_type="project_tag_added",
            description=f"Tag '{tag.name}' added to project",
            project_id=project.id,
            user_id=current_user["id"]
        )
    )
    
    return project

@router.delete("/{project_id}/tags/{tag_id}", response_model=ProjectSchema)
async def remove_tag_from_project(
    project_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Remove a tag from a project.
    """
    # Check if project exists
    project = project_crud.get(db, id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if tag exists
    tag = tag_crud.get(db, id=tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Check if tag is added to project
    if tag not in project.tags:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag is not added to this project"
        )
    
    # Remove tag from project
    project.tags.remove(tag)
    db.commit()
    db.refresh(project)
    
    # Log activity
    activity.create(
        db,
        ActivityCreate(
            activity_type="project_tag_removed",
            description=f"Tag '{tag.name}' removed from project",
            project_id=project.id,
            user_id=current_user["id"]
        )
    )
    
    return project

@router.get("/{project_id}/tags", response_model=List[TagSchema])
async def get_project_tags(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all tags associated with a project.
    """
    project = project_crud.get(db, id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return project.tags

@router.put("/{project_id}/tags", response_model=ProjectSchema)
async def update_project_tags(
    project_id: int,
    tag_ids: List[int],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update all tags for a project. This will replace existing tags with the new list.
    """
    # Check if project exists
    project = project_crud.get(db, id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
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
    old_tags = set(project.tags)
    new_tags = set(tags)
    removed_tags = old_tags - new_tags
    added_tags = new_tags - old_tags
    
    # Update project tags
    project.tags = tags
    db.commit()
    db.refresh(project)
    
    # Log activities
    for tag in removed_tags:
        activity.create(
            db,
            ActivityCreate(
                activity_type="project_tag_removed",
                description=f"Tag '{tag.name}' removed from project",
                project_id=project.id,
                user_id=current_user["id"]
            )
        )
    
    for tag in added_tags:
        activity.create(
            db,
            ActivityCreate(
                activity_type="project_tag_added",
                description=f"Tag '{tag.name}' added to project",
                project_id=project.id,
                user_id=current_user["id"]
            )
        )
    
    return project

@router.post("/{project_id}/follow")
async def follow_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Follow a project."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user in project.followers:
        raise HTTPException(status_code=400, detail="Already following this project")

    project.followers.append(user)
    db.commit()

    # Notify project owner
    if project.created_by != current_user["id"]:
        notification_service.create_notification(
            db=db,
            user_id=project.created_by,
            title="New Project Follower",
            content=f"{user.full_name} started following your project '{project.name}'",
            notification_type="project_follow",
            reference_type="project",
            reference_id=project_id
        )

    return {"message": "Successfully followed project"}

@router.delete("/{project_id}/unfollow")
async def unfollow_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Unfollow a project."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user not in project.followers:
        raise HTTPException(status_code=400, detail="Not following this project")

    project.followers.remove(user)
    db.commit()

    return {"message": "Successfully unfollowed project"} 