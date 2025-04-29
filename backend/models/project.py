from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from .base import Base

# Association table for project members
project_members = Table(
    'project_members',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role', String(50), default='member'),  # Optional: track member role in project
    Column('joined_at', DateTime(timezone=True), server_default=func.now())
)

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="planning")
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    budget = Column(Float, default=0.0)
    priority = Column(Integer, default=1)
    tags = Column(String(255), nullable=True)
    
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Use strings for relationship to avoid circular imports
    creator = relationship("User", foreign_keys=[created_by], backref="created_projects")
    
    # Add many-to-many relationship with users through project_members table
    members = relationship("User", secondary=project_members, backref="projects")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="project")

    def __repr__(self):
        return f"<Project {self.name}>" 