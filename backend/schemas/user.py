from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from .role import Role


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    is_active: Optional[bool] = True
    is_superuser: bool = False
    profile_image_url: Optional[str] = None
    job_title: Optional[str] = None
    bio: Optional[str] = None
    profession: Optional[str] = None
    expertise: Optional[List[str]] = []
    skills: Optional[List[str]] = []
    experience_level: Optional[str] = None
    notes: Optional[str] = None
    certifications: Optional[List[str]] = []
    preferred_working_hours: Optional[str] = None
    specializations: Optional[List[str]] = []


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
    profession: Optional[str] = None
    expertise: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    experience_level: Optional[str] = None
    notes: Optional[str] = None
    certifications: Optional[List[str]] = None
    preferred_working_hours: Optional[str] = None
    specializations: Optional[List[str]] = None


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


class UserExpertise(BaseModel):
    """Schema for user expertise details"""
    expertise: List[str]
    skills: List[str]
    experience_level: str
    certifications: List[str]
    specializations: List[str]

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """Detailed user profile information"""
    id: int
    username: str
    email: EmailStr
    full_name: str
    profile_image_url: Optional[str]
    job_title: Optional[str]
    bio: Optional[str]
    profession: Optional[str]
    expertise: Optional[List[str]]
    skills: Optional[List[str]]
    experience_level: Optional[str]
    notes: Optional[str]
    certifications: Optional[List[str]]
    preferred_working_hours: Optional[str]
    specializations: Optional[List[str]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True 