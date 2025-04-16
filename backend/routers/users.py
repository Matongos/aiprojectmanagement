from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from routers.auth import get_current_user
from services import user_service

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

    class Config:
        schema_extra = {
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
    # Check if user is superuser
    if not current_user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Activate user using the service
    user, error = user_service.activate_user(db, user_id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return user

@router.patch("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Deactivate a user.
    Superusers can deactivate any user.
    Users cannot deactivate themselves.
    """
    # Check if user is superuser
    if not current_user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Prevent self-deactivation
    if current_user["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account"
        )
    
    # Deactivate user using the service
    user, error = user_service.deactivate_user(db, user_id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return user

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
    Delete a user account.
    Only superusers can delete other users' accounts.
    """
    # Check if user is superuser
    if not current_user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Prevent superuser from deleting their own account through this endpoint
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete own account through this endpoint. Use /users/me endpoint instead."
        )
    
    # Delete user using the service
    error = user_service.delete_user(db, user_id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "User deleted successfully"}

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