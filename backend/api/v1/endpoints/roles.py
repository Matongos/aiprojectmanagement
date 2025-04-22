from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api import deps
from crud import role as role_crud
from schemas.role import Role, RoleCreate, RoleUpdate, Permission, PermissionCreate
from ....models.user import User

router = APIRouter()

@router.get("/roles/", response_model=List[Role])
def get_roles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db)
):
    """
    Retrieve all roles.
    """
    roles = role_crud.get_roles(db, skip=skip, limit=limit)
    return roles

@router.post("/roles/", response_model=Role)
def create_role(
    role_in: RoleCreate,
    db: Session = Depends(deps.get_db)
):
    """
    Create new role.
    """
    role = role_crud.get_role_by_name(db, name=role_in.name)
    if role:
        raise HTTPException(
            status_code=400,
            detail="Role with this name already exists."
        )
    return role_crud.create_role(db, obj_in=role_in)

@router.put("/roles/{role_id}", response_model=Role)
def update_role(
    role_id: int,
    role_in: RoleUpdate,
    db: Session = Depends(deps.get_db)
):
    """
    Update a role.
    """
    role = role_crud.get_role(db, id=role_id)
    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )
    return role_crud.update_role(db, db_obj=role, obj_in=role_in)

@router.delete("/roles/{role_id}", response_model=Role)
def delete_role(
    role_id: int,
    db: Session = Depends(deps.get_db)
):
    """
    Delete a role.
    """
    role = role_crud.get_role(db, id=role_id)
    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )
    return role_crud.delete_role(db, id=role_id)

@router.post("/roles/{role_id}/permissions/{permission_id}", response_model=Role)
def add_permission_to_role(
    role_id: int,
    permission_id: int,
    db: Session = Depends(deps.get_db)
):
    """
    Add a permission to a role.
    """
    role = role_crud.get_role(db, id=role_id)
    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )
    try:
        return role_crud.add_permission_to_role(db, role_id=role_id, permission_id=permission_id)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

@router.delete("/roles/{role_id}/permissions/{permission_id}", response_model=Role)
def remove_permission_from_role(
    role_id: int,
    permission_id: int,
    db: Session = Depends(deps.get_db)
):
    """
    Remove a permission from a role.
    """
    role = role_crud.get_role(db, id=role_id)
    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )
    try:
        return role_crud.remove_permission_from_role(db, role_id=role_id, permission_id=permission_id)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

@router.get("/permissions/", response_model=List[Permission])
def get_permissions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db)
):
    """
    Retrieve all permissions.
    """
    permissions = role_crud.get_permissions(db, skip=skip, limit=limit)
    return permissions

@router.post("/permissions/", response_model=Permission)
def create_permission(
    permission_in: PermissionCreate,
    db: Session = Depends(deps.get_db)
):
    """
    Create new permission.
    """
    permission = role_crud.get_permission_by_name(db, name=permission_in.name)
    if permission:
        raise HTTPException(
            status_code=400,
            detail="Permission with this name already exists."
        )
    return role_crud.create_permission(db, obj_in=permission_in)

@router.delete("/permissions/{permission_id}", response_model=Permission)
def delete_permission(
    *,
    db: Session = Depends(deps.get_db),
    permission_id: int,
    current_user: User = Depends(deps.get_current_active_superuser),
):
    """
    Delete a permission.
    """
    permission = role_crud.get_permission(db, id=permission_id)
    if not permission:
        raise HTTPException(
            status_code=404,
            detail="Permission not found",
        )
    permission = role_crud.delete_permission(db, id=permission_id)
    return permission 