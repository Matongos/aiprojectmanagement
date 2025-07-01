from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import logging

from database import get_db
from routers.auth import get_current_user
from services import user_service
from schemas.user import User

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


@router.get("/team-directory", response_model=List[dict])
async def get_team_directory(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get team directory based on user permissions:
    - Superusers: See all users in the system
    - General users: See only members from their projects
    """
    try:
        from models.task import Task
        from models.project import Project, ProjectMember, ProjectRole
        
        if current_user.get("is_superuser"):
            # Superusers see all users
            users = user_service.get_users(db, skip=0, limit=1000)
            
            # Get task information for each user
            team_members = []
            for user in users:
                # Get user's active tasks
                user_tasks = db.query(Task).filter(
                    Task.assigned_to == user["id"],
                    Task.state.in_(['in_progress', 'approved', 'changes_requested'])
                ).all()
                
                # Get projects where user is a member
                user_projects = db.query(Project).join(
                    ProjectMember, Project.id == ProjectMember.project_id
                ).filter(
                    ProjectMember.user_id == user["id"]
                ).all()
                
                team_members.append({
                    "id": user["id"],
                    "name": user["full_name"] or user["username"],
                    "job_title": user.get("job_title"),
                    "project_names": [project.name for project in user_projects],
                    "has_active_task": len(user_tasks) > 0,
                    "tasks": [
                        {
                            "id": task.id,
                            "name": task.name,
                            "state": task.state,
                            "project_id": task.project_id,
                            "project_name": task.project.name if task.project else "Unknown",
                            "deadline": task.deadline.isoformat() if task.deadline else None,
                            "priority": task.priority,
                            "assigned_to": task.assigned_to
                        } for task in user_tasks
                    ]
                })
            
            return team_members
            
        else:
            # General users see only members from their projects
            # Get projects where user is a member or has tasks
            user_projects = db.query(Project).join(
                ProjectMember, Project.id == ProjectMember.project_id
            ).filter(
                ProjectMember.user_id == current_user["id"]
            ).all()
            
            # Also get projects where user has assigned tasks
            projects_with_tasks = db.query(Project).join(
                Task, Project.id == Task.project_id
            ).filter(
                Task.assigned_to == current_user["id"]
            ).all()
            
            # Combine and deduplicate projects
            all_user_projects = list(set(user_projects + projects_with_tasks))
            
            if not all_user_projects:
                return []
            
            # Get all members from these projects
            project_ids = [project.id for project in all_user_projects]
            
            # Get all project members from user's projects
            project_members = db.query(ProjectMember).filter(
                ProjectMember.project_id.in_(project_ids)
            ).all()
            
            # Get unique user IDs
            member_user_ids = list(set([pm.user_id for pm in project_members]))
            
            # Get user details
            users = user_service.get_users_by_ids(db, member_user_ids)
            
            # Build team directory
            team_members = []
            for user in users:
                # Get user's active tasks in user's projects
                user_tasks = db.query(Task).filter(
                    Task.assigned_to == user["id"],
                    Task.project_id.in_(project_ids),
                    Task.state.in_(['in_progress', 'approved', 'changes_requested'])
                ).all()
                
                # Get projects where this user is a member (from user's projects)
                user_projects = db.query(Project).join(
                    ProjectMember, Project.id == ProjectMember.project_id
                ).filter(
                    ProjectMember.user_id == user["id"],
                    Project.id.in_(project_ids)
                ).all()
                
                team_members.append({
                    "id": user["id"],
                    "name": user["full_name"] or user["username"],
                    "job_title": user.get("job_title"),
                    "project_names": [project.name for project in user_projects],
                    "has_active_task": len(user_tasks) > 0,
                    "tasks": [
                        {
                            "id": task.id,
                            "name": task.name,
                            "state": task.state,
                            "project_id": task.project_id,
                            "project_name": task.project.name if task.project else "Unknown",
                            "deadline": task.deadline.isoformat() if task.deadline else None,
                            "priority": task.priority,
                            "assigned_to": task.assigned_to
                        } for task in user_tasks
                    ]
                })
            
            return team_members
            
    except Exception as e:
        logger.error(f"Error fetching team directory: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching team directory: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return current_user

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