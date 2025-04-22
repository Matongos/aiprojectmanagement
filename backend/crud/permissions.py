from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

from models.role import Permission
from schemas.permissions import PermissionCreate, PermissionUpdate

def get_permission(db: Session, permission_id: int) -> Optional[Permission]:
    return db.query(Permission).filter(Permission.id == permission_id).first()

def get_permission_by_name(db: Session, name: str) -> Optional[Permission]:
    return db.query(Permission).filter(Permission.name == name).first()

def get_permissions(db: Session, skip: int = 0, limit: int = 100) -> List[Permission]:
    return db.query(Permission).offset(skip).limit(limit).all()

def create_permission(db: Session, permission: PermissionCreate) -> Permission:
    db_permission = Permission(**permission.model_dump())
    try:
        db.add(db_permission)
        db.commit()
        db.refresh(db_permission)
        return db_permission
    except IntegrityError:
        db.rollback()
        raise ValueError(f"Permission with name '{permission.name}' already exists")

def update_permission(db: Session, permission_id: int, permission: PermissionUpdate) -> Optional[Permission]:
    db_permission = get_permission(db, permission_id)
    if not db_permission:
        return None
    
    update_data = permission.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_permission, field, value)
    
    try:
        db.commit()
        db.refresh(db_permission)
        return db_permission
    except IntegrityError:
        db.rollback()
        raise ValueError(f"Permission with name '{permission.name}' already exists")

def delete_permission(db: Session, permission_id: int) -> bool:
    db_permission = get_permission(db, permission_id)
    if not db_permission:
        return False
    
    try:
        db.delete(db_permission)
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        raise ValueError("Cannot delete permission as it is being used by roles") 