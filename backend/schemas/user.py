from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from .role import Role


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    is_active: bool = True
    is_superuser: bool = False
    profile_image_url: Optional[str] = None
    job_title: Optional[str] = None
    bio: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    profile_image_url: Optional[str] = None
    job_title: Optional[str] = None
    bio: Optional[str] = None


class User(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    roles: Optional[List[Role]] = []
    email_notifications_enabled: Optional[bool] = True

    class Config:
        from_attributes = True


class UserInDB(User):
    hashed_password: str 