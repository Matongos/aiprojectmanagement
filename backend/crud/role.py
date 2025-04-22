from sqlalchemy.orm import Session
from typing import List, Optional, Union, Dict, Any
from models.role import Role, Permission
from schemas.roles import RoleCreate, RoleUpdate, PermissionCreate
from .base import CRUDBase

class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Role]:
        return db.query(Role).filter(Role.name == name).first()

    def create(self, db: Session, *, obj_in: RoleCreate) -> Role:
        db_obj = Role(
            name=obj_in.name,
            description=obj_in.description,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        # Add permissions to role
        if hasattr(obj_in, 'permission_ids') and obj_in.permission_ids:
            for permission_id in obj_in.permission_ids:
                permission = db.query(Permission).filter(Permission.id == permission_id).first()
                if permission:
                    db_obj.permissions.append(permission)
            db.commit()
            db.refresh(db_obj)
        
        return db_obj

    def update(
        self, db: Session, *, db_obj: Role, obj_in: Union[RoleUpdate, Dict[str, Any]]
    ) -> Role:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def add_permission_to_role(
        self, db: Session, *, role_id: int, permission_id: int
    ) -> Role:
        role = self.get(db, id=role_id)
        permission = db.query(Permission).filter(Permission.id == permission_id).first()
        if not permission:
            raise ValueError("Permission not found")
        role.permissions.append(permission)
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

    def remove_permission_from_role(
        self, db: Session, *, role_id: int, permission_id: int
    ) -> Role:
        role = self.get(db, id=role_id)
        permission = db.query(Permission).filter(Permission.id == permission_id).first()
        if not permission:
            raise ValueError("Permission not found")
        role.permissions.remove(permission)
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionCreate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Permission]:
        return db.query(Permission).filter(Permission.name == name).first()

    def create(self, db: Session, *, obj_in: PermissionCreate) -> Permission:
        db_obj = Permission(
            name=obj_in.name,
            description=obj_in.description,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

role = CRUDRole(Role)
permission = CRUDPermission(Permission)

def get_role(db: Session, role_id: int) -> Optional[Role]:
    return db.query(Role).filter(Role.id == role_id).first()

def get_roles(db: Session, skip: int = 0, limit: int = 100) -> List[Role]:
    return db.query(Role).offset(skip).limit(limit).all()

def update_role(db: Session, role_id: int, role: RoleUpdate) -> Optional[Role]:
    db_role = get_role(db, role_id)
    if not db_role:
        return None
    
    update_data = role.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_role, field, value)
    
    db.commit()
    db.refresh(db_role)
    return db_role

def delete_role(db: Session, role_id: int) -> bool:
    db_role = get_role(db, role_id)
    if not db_role:
        return False
    
    db.delete(db_role)
    db.commit()
    return True

def get_permission(db: Session, permission_id: int) -> Optional[Permission]:
    return db.query(Permission).filter(Permission.id == permission_id).first()

def get_permissions(db: Session, skip: int = 0, limit: int = 100) -> List[Permission]:
    return db.query(Permission).offset(skip).limit(limit).all()

def delete_permission(db: Session, permission_id: int) -> bool:
    db_permission = get_permission(db, permission_id)
    if not db_permission:
        return False
    
    db.delete(db_permission)
    db.commit()
    return True 