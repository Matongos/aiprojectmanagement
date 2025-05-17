from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Table, JSON, Date, Text, Float, select, Enum, CheckConstraint
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.sql import func
from .base import Base
from .milestone import Milestone  # Import Milestone from its dedicated module
from .task import Task  # Import Task model
from .tag import Tag  # Import Tag model
import enum

# Association table for project tags
project_tag = Table(
    'project_tag',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
    extend_existing=True
)

# Association table for project followers
project_followers = Table(
    'project_followers',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    extend_existing=True
)

class ProjectStage(str, enum.Enum):
    TODO = "to_do"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"

class ProjectMember(Base):
    __tablename__ = "project_members"

    project_id = Column(Integer, ForeignKey('projects.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role = Column(String, default='member')
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships with overlaps parameters
    project = relationship("Project", back_populates="project_members", overlaps="members")
    user = relationship("User", back_populates="project_memberships", overlaps="member_of_projects")

    def __repr__(self):
        return f"<ProjectMember {self.project_id}:{self.user_id}>"

class StageDefinition(Base):
    __tablename__ = "stage_definitions"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Project(Base):
    __tablename__ = "projects"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    key = Column(String, unique=True, index=True)
    status = Column(String, nullable=False, default="active")
    stage_id = Column(Integer, ForeignKey("stage_definitions.id"), nullable=True)
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
    stage = relationship("StageDefinition")
    
    # Followers relationship
    followers = relationship(
        "User",
        secondary=project_followers,
        back_populates="followed_projects"
    )

    # Add task_count as a column property
    task_count = column_property(
        select(func.count(Task.id))
        .where(Task.project_id == id)
        .correlate_except(Task)
        .scalar_subquery()
    )

    def calculate_progress(self):
        """Calculate project progress based on task completion."""
        tasks = self.tasks
        if not tasks:
            return 0.0
        return sum(task.progress for task in tasks) / len(tasks)

    def __repr__(self):
        return f"<Project {self.name}>" 