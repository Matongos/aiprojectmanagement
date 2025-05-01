from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Table, JSON, Date, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base

# Association table for project tags
project_tag = Table(
    'project_tag',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class ProjectMember(Base):
    __tablename__ = "project_members"

    project_id = Column(Integer, ForeignKey('projects.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role = Column(String, default='member')
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships with overlaps parameters
    project = relationship("Project", back_populates="project_members", overlaps="members")
    user = relationship("User", back_populates="project_memberships", overlaps="member_of_projects")

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    key = Column(String, unique=True, index=True)
    status = Column(String, nullable=False, default="active")
    privacy_level = Column(String, nullable=False, default="private")
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    color = Column(String, nullable=False, default="#3498db")
    is_template = Column(Boolean, nullable=False, default=False)
    progress = Column(Float, default=0.0, comment='Project progress percentage')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_projects")
    project_members = relationship("ProjectMember", back_populates="project", overlaps="members")
    members = relationship(
        "User",
        secondary="project_members",
        back_populates="member_of_projects",
        overlaps="project_memberships,project_members"
    )
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    stages = relationship("TaskStage", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=project_tag, back_populates="projects")
    activities = relationship("Activity", back_populates="project", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="project", cascade="all, delete-orphan")

    def calculate_progress(self):
        """Calculate project progress based on task completion."""
        tasks = self.tasks
        if not tasks:
            return 0.0
        return sum(task.progress for task in tasks) / len(tasks)

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    color = Column(String(7), default="#3498db")
    
    # Relationships
    projects = relationship("Project", secondary=project_tag, back_populates="tags")

class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    due_date = Column(Date, nullable=True)
    completed_date = Column(Date, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="milestones")
    creator = relationship("User", foreign_keys=[created_by])
    tasks = relationship("Task", back_populates="milestone") 