from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    profile_image_url = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    roles = relationship("Role", secondary="user_role", back_populates="users", lazy="joined")
    projects = relationship("ProjectMember", back_populates="user", foreign_keys="ProjectMember.user_id")
    tasks = relationship("TaskAssignment", back_populates="user", foreign_keys="TaskAssignment.user_id")
    created_projects = relationship("Project", back_populates="creator", foreign_keys="Project.created_by")
    created_tasks = relationship("Task", back_populates="creator", foreign_keys="Task.created_by")
    time_entries = relationship("TimeEntry", back_populates="user", foreign_keys="TimeEntry.user_id")
    notifications = relationship("Notification", back_populates="user", foreign_keys="Notification.user_id")
    comments = relationship("Comment", back_populates="user", foreign_keys="Comment.user_id") 