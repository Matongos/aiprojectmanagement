from typing import List, Optional
from sqlalchemy.orm import Session
from models.role import Role, Permission, user_role
from schemas.roles import RoleCreate, RoleUpdate, PermissionCreate
from database import get_db

async def create_role(role: RoleCreate) -> Role:
    db = next(get_db())
    db_role = Role(
        name=role.name,
        description=role.description
    )
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    
    # Add permissions to role
    if role.permission_ids:
        for permission_id in role.permission_ids:
            permission = db.query(Permission).filter(Permission.id == permission_id).first()
            if permission:
                db_role.permissions.append(permission)
        db.commit()
        db.refresh(db_role)
    
    return db_role

async def get_role(role_id: int) -> Optional[Role]:
    db = next(get_db())
    return db.query(Role).filter(Role.id == role_id).first()

async def get_roles() -> List[Role]:
    db = next(get_db())
    return db.query(Role).all()

async def update_role(role_id: int, role_update: RoleUpdate) -> Optional[Role]:
    db = next(get_db())
    db_role = db.query(Role).filter(Role.id == role_id).first()
    if not db_role:
        return None
    
    # Update basic fields
    if role_update.name is not None:
        db_role.name = role_update.name
    if role_update.description is not None:
        db_role.description = role_update.description
    
    # Update permissions
    if role_update.permission_ids is not None:
        db_role.permissions = []
        for permission_id in role_update.permission_ids:
            permission = db.query(Permission).filter(Permission.id == permission_id).first()
            if permission:
                db_role.permissions.append(permission)
    
    db.commit()
    db.refresh(db_role)
    return db_role

async def delete_role(role_id: int) -> bool:
    db = next(get_db())
    db_role = db.query(Role).filter(Role.id == role_id).first()
    if not db_role:
        return False
    
    db.delete(db_role)
    db.commit()
    return True

async def create_permission(permission: PermissionCreate) -> Permission:
    db = next(get_db())
    db_permission = Permission(
        name=permission.name,
        description=permission.description
    )
    db.add(db_permission)
    db.commit()
    db.refresh(db_permission)
    return db_permission

async def get_permissions() -> List[Permission]:
    db = next(get_db())
    return db.query(Permission).all()

async def assign_role_to_user(user_id: int, role_id: int) -> bool:
    db = next(get_db())
    
    # Check if role exists
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        return False
    
    # Check if assignment already exists
    existing = db.execute(
        user_role.select().where(
            user_role.c.user_id == user_id,
            user_role.c.role_id == role_id
        )
    ).first()
    
    if existing:
        return True
    
    # Create new assignment
    db.execute(
        user_role.insert().values(
            user_id=user_id,
            role_id=role_id
        )
    )
    db.commit()
    return True

async def remove_role_from_user(user_id: int, role_id: int) -> bool:
    db = next(get_db())
    result = db.execute(
        user_role.delete().where(
            user_role.c.user_id == user_id,
            user_role.c.role_id == role_id
        )
    )
    db.commit()
    return result.rowcount > 0 