from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import logging
from datetime import datetime

from database import get_db
from routers.auth import get_current_user
from services import user_service
from schemas.user import User
from models.user import User as UserModel
from models.project import Project, ProjectMember
from models.task import Task
from sqlalchemy import or_, and_

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={401: {"description": "Unauthorized"}}
)

# Models
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    profile_image_url: Optional[str] = None
    job_title: Optional[str] = None
    bio: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    profile_image_url: Optional[str] = None
    job_title: Optional[str] = None
    bio: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str
    is_active: bool = True
    is_superuser: bool = False
    profile_image_url: Optional[str] = None
    job_title: Optional[str] = None
    bio: Optional[str] = None

class UserProfileUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None  # New password if changing
    current_password: Optional[str] = None  # Required if changing password
    profile_image_url: Optional[str] = None
    job_title: Optional[str] = None
    bio: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "newusername",
                "email": "newemail@example.com",
                "full_name": "New Full Name",
                "password": "new_password",
                "current_password": "current_password",
                "profile_image_url": "https://example.com/image.jpg",
                "job_title": "Software Engineer",
                "bio": "New bio text"
            }
        }
    }

class TeamDirectoryTask(BaseModel):
    id: int
    name: str
    state: str
    project_id: int
    project_name: str
    deadline: Optional[datetime] = None
    priority: Optional[str] = None
    assigned_to: Optional[int] = None

class TeamDirectoryUser(BaseModel):
    id: int
    name: str
    job_title: Optional[str]
    project_names: List[str]
    has_active_task: bool
    tasks: List[TeamDirectoryTask]

# Routes
@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all users.
    Only superusers can access this endpoint.
    """
    # Check if user is superuser
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Get users using the service
    users = user_service.get_users(db, skip, limit)
    
    return users

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return current_user

@router.get("/team-directory", response_model=List[TeamDirectoryUser])
async def get_team_directory(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all users in the same projects as the current user, with their tasks and shared projects.
    Superusers see all users, starting with those with active tasks.
    """
    user_id = current_user["id"]
    is_superuser = current_user.get("is_superuser", False)

    # Helper: get active task states
    active_states = ["todo", "in_progress", "changes_requested", "approved"]

    if is_superuser:
        users = db.query(UserModel).all()
    else:
        # Get all project IDs where user is a member or has a task
        project_ids = set(
            [pm.project_id for pm in db.query(ProjectMember).filter(ProjectMember.user_id == user_id).all()]
        )
        task_project_ids = set(
            [t.project_id for t in db.query(Task).filter(Task.assigned_to == user_id).all()]
        )
        all_project_ids = project_ids | task_project_ids
        # Get all users in those projects
        user_ids = set()
        for pid in all_project_ids:
            members = db.query(ProjectMember).filter(ProjectMember.project_id == pid).all()
            user_ids.update([m.user_id for m in members])
        users = db.query(UserModel).filter(UserModel.id.in_(user_ids)).all()

    # Build user info
    user_list = []
    for user in users:
        # Get all projects this user is in
        user_project_ids = set([pm.project_id for pm in db.query(ProjectMember).filter(ProjectMember.user_id == user.id).all()])
        user_projects = db.query(Project).filter(Project.id.in_(user_project_ids)).all()
        project_names = [p.name for p in user_projects]
        # Get all tasks for this user
        user_tasks = db.query(Task).filter(Task.assigned_to == user.id).all()
        # For each task, get project name
        tasks_out = [
            TeamDirectoryTask(
                id=t.id,
                name=t.name,
                state=t.state,
                project_id=t.project_id,
                project_name=next((p.name for p in user_projects if p.id == t.project_id), None),
                deadline=t.deadline,
                priority=t.priority,
                assigned_to=t.assigned_to
            )
            for t in user_tasks
        ]
        # Determine if user has any active task
        has_active_task = any(t.state in active_states for t in user_tasks)
        user_list.append(TeamDirectoryUser(
            id=user.id,
            name=user.full_name,
            job_title=user.job_title,
            project_names=project_names,
            has_active_task=has_active_task,
            tasks=tasks_out
        ))
    # Sort: users with active tasks first
    user_list.sort(key=lambda u: not u.has_active_task)
    return user_list

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a user by ID.
    Users can view their own profile.
    Superusers can view any profile.
    """
    # Check permissions
    if current_user["id"] != user_id and not current_user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Get user using the service
    user = user_service.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new user.
    Only superusers can create new users.
    """
    # Check if user is superuser
    if not current_user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Convert Pydantic model to dict
    user_dict = user_data.dict()
    
    # Create user using the service
    user, error = user_service.create_user(db, user_dict)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a user.
    Users can update their own profile.
    Superusers can update any profile.
    """
    # Check permissions
    if current_user["id"] != user_id and not current_user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if user exists
    user = user_service.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Convert Pydantic model to dict
    update_dict = user_data.dict(exclude_unset=True)
    
    # Update user using the service
    updated_user, error = user_service.update_user(db, user_id, update_dict)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return updated_user

@router.patch("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Activate a user.
    Only superusers can activate users.
    """
    if not current_user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    updated_user, error = user_service.update_user(db, user_id, {"is_active": True})
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return updated_user

@router.patch("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Deactivate a user.
    Only superusers can deactivate users.
    """
    if not current_user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    updated_user, error = user_service.update_user(db, user_id, {"is_active": False})
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return updated_user

@router.patch("/{user_id}/make-admin", response_model=UserResponse)
async def make_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Make a user an admin.
    Only superusers can make other users admins.
    """
    if not current_user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    updated_user, error = user_service.update_user(db, user_id, {"is_superuser": True})
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return updated_user

@router.patch("/{user_id}/remove-admin", response_model=UserResponse)
async def remove_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Remove admin privileges from a user.
    Only superusers can remove admin privileges.
    """
    if not current_user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    updated_user, error = user_service.update_user(db, user_id, {"is_superuser": False})
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return updated_user

@router.delete("/me")
async def delete_user_me(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete current user's own account.
    """
    user_id = current_user["id"]
    
    # Delete user using the service
    error = user_service.delete_user(db, user_id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Account deleted successfully"}

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a user.
    Users can delete their own account.
    Superusers can delete any account.
    """
    # Check permissions
    if current_user["id"] != user_id and not current_user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if user exists
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Delete user using the service
    error = user_service.delete_user(db, user_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return None

@router.patch("/me/profile", response_model=UserResponse)
async def update_my_profile(
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update current user's profile including password.
    When changing password, current_password must be provided and verified.
    
    The current user is determined by the authentication token.
    You can see your current user information in the response.
    """
    print(f"Updating profile for user: {current_user['username']} (ID: {current_user['id']})")
    print(f"Current user details: {current_user}")
    
    # Add current user info to the response
    response_data = {
        "message": "Profile update initiated",
        "current_user": {
            "id": current_user["id"],
            "username": current_user["username"],
            "email": current_user["email"],
            "full_name": current_user["full_name"]
        },
        "updates_requested": profile_data.dict(exclude_unset=True)
    }
    
    # Convert Pydantic model to dict
    update_dict = profile_data.dict(exclude_unset=True)
    
    # Use the profile-specific update service
    updated_user, error = user_service.update_user_profile(db, current_user["id"], update_dict)
    
    if error:
        print(f"Error updating profile: {error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": error,
                "current_user": {
                    "id": current_user["id"],
                    "username": current_user["username"],
                    "email": current_user["email"],
                    "full_name": current_user["full_name"]
                }
            }
        )
    
    print(f"Profile updated successfully for user: {current_user['username']}")
    print(f"Updated user details: {updated_user}")
    
    # Add success message to the response
    response_data.update({
        "message": "Profile updated successfully",
        "updated_user": updated_user
    })
    
    return updated_user

@router.put("/me/email-preferences", response_model=UserResponse)
def update_email_preferences(
    enable_email: bool = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    Update email notification preferences for the current user.
    
    Args:
        enable_email: Whether to enable email notifications
        
    Returns:
        Updated user object
    """
    user = user_service.get_user_by_id(db, current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # If the email_notifications_enabled field doesn't exist yet, add it
    try:
        update_data = {"email_notifications_enabled": enable_email}
        updated_user, error = user_service.update_user(db, current_user["id"], update_data)
        if error:
            raise HTTPException(status_code=400, detail=error)
        return updated_user
    except Exception as e:
        logger.error(f"Error updating email preferences: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Error updating email preferences. The feature may not be available yet."
        ) 