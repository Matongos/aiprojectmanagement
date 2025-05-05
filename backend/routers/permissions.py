from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.role import Permission
from routers.auth import get_current_user
from schemas.permissions import PermissionCreate, PermissionResponse, PermissionUpdate

router = APIRouter(
    prefix="/permissions",
    tags=["permissions"]
)

@router.get("/", response_model=List[PermissionResponse])
async def list_permissions(db: Session = Depends(get_db)):
    """Get all permissions"""
    permissions = db.query(Permission).all()
    return permissions

@router.post("/", response_model=PermissionResponse)
async def create_permission(permission: PermissionCreate, db: Session = Depends(get_db)):
    """Create a new permission"""
    db_permission = Permission(
        name=permission.name,
        description=permission.description
    )
    db.add(db_permission)
    db.commit()
    db.refresh(db_permission)
    return db_permission

@router.get("/{permission_id}", response_model=PermissionResponse)
async def get_permission(permission_id: int, db: Session = Depends(get_db)):
    """Get a specific permission by ID"""
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    return permission

@router.put("/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: int,
    permission_update: PermissionUpdate,
    db: Session = Depends(get_db)
):
    """Update a permission"""
    db_permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not db_permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    if permission_update.name is not None:
        db_permission.name = permission_update.name
    if permission_update.description is not None:
        db_permission.description = permission_update.description
    
    db.commit()
    db.refresh(db_permission)
    return db_permission

@router.delete("/{permission_id}")
async def delete_permission(permission_id: int, db: Session = Depends(get_db)):
    """Delete a permission"""
    db_permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not db_permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    db.delete(db_permission)
    db.commit()
    return {"message": "Permission deleted successfully"} 