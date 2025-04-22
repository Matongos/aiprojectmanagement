from pydantic import BaseModel, Field
from typing import Optional

class PermissionBase(BaseModel):
    name: str = Field(..., description="Name of the permission")
    description: Optional[str] = Field(None, description="Description of the permission")

class PermissionCreate(PermissionBase):
    pass

class PermissionUpdate(PermissionBase):
    name: Optional[str] = Field(None, description="Name of the permission")
    description: Optional[str] = Field(None, description="Description of the permission")

class PermissionResponse(PermissionBase):
    id: int = Field(..., description="ID of the permission")

    class Config:
        from_attributes = True 