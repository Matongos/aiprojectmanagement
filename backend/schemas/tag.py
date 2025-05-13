from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator

class TagBase(BaseModel):
    """Base schema for tag data validation"""
    name: str = Field(..., min_length=1, max_length=50, description="Tag name (required)")
    color: Optional[int] = Field(default=1, ge=1, le=11, description="Color index (1-11)")
    active: bool = Field(default=True, description="Whether the tag is active")

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Tag name cannot be empty')
        return v.strip()

class TagCreate(TagBase):
    """Schema for tag creation"""
    pass

class TagUpdate(BaseModel):
    """Schema for tag updates"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[int] = Field(None, ge=1, le=11)
    active: Optional[bool] = None

    @validator('name')
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Tag name cannot be empty')
        return v.strip() if v else v

class Tag(TagBase):
    """Complete tag schema with all fields"""
    id: int
    create_uid: Optional[int]
    create_date: datetime
    write_uid: Optional[int]
    write_date: Optional[datetime]

    class Config:
        from_attributes = True 