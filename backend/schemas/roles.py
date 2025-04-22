from pydantic import BaseModel, Field
from typing import List, Optional

class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None

class PermissionCreate(PermissionBase):
    pass

class Permission(PermissionBase):
    id: int

    class Config:
        from_attributes = True

class RoleBase(BaseModel):
    name: str = Field(..., description="Name of the role")
    description: Optional[str] = Field(None, description="Description of the role")

class RoleCreate(RoleBase):
    permission_ids: List[int] = Field(default_factory=list, description="List of permission IDs to assign to the role")

class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Name of the role")
    description: Optional[str] = Field(None, description="Description of the role")
    permission_ids: Optional[List[int]] = Field(None, description="List of permission IDs to assign to the role")

class Role(RoleBase):
    id: int
    permissions: List[Permission]

    class Config:
        from_attributes = True

class UserRole(BaseModel):
    user_id: int
    role_id: int

    class Config:
        from_attributes = True

class PermissionInRole(BaseModel):
    id: int = Field(..., description="ID of the permission")
    name: str = Field(..., description="Name of the permission")
    description: Optional[str] = Field(None, description="Description of the permission")

    class Config:
        from_attributes = True

class RoleResponse(RoleBase):
    id: int = Field(..., description="ID of the role")
    permissions: List[PermissionInRole] = Field(default_factory=list, description="List of permissions assigned to the role")

    class Config:
        from_attributes = True 