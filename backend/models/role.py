from sqlalchemy import Column, Integer, String, Table, ForeignKey, Index
from sqlalchemy.orm import relationship
from database import Base

# Association table for role-permission relationship
role_permission = Table(
    'role_permission',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Index('ix_role_permission_role_id', 'role_id'),
    Index('ix_role_permission_permission_id', 'permission_id')
)

# Association table for user-role relationship
user_role = Table(
    'user_role',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Index('ix_user_role_user_id', 'user_id'),
    Index('ix_user_role_role_id', 'role_id')
)

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(200), nullable=True)

    # Relationships using string references to avoid circular imports
    permissions = relationship("Permission", secondary=role_permission, back_populates="roles", lazy="joined")
    users = relationship("User", secondary=user_role, back_populates="roles", lazy="joined")

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(200), nullable=True)

    # Relationships
    roles = relationship("Role", secondary=role_permission, back_populates="permissions", lazy="joined") 