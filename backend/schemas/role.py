from typing import Optional, List
from pydantic import BaseModel

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
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    permission_ids: List[int] = []

class RoleUpdate(RoleBase):
    permission_ids: Optional[List[int]] = None

class Role(RoleBase):
    id: int
    permissions: List[Permission] = []

    class Config:
        from_attributes = True 