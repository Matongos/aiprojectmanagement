from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Table, JSON, Date, Text, Float, select, Enum, CheckConstraint, text
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.sql import func
from .base import Base
from .milestone import Milestone  # Import Milestone from its dedicated module
from .task import Task  # Import Task model
from .tag import Tag  # Import Tag model
from .metrics import ProjectMetrics, ResourceMetrics
import enum
from datetime import datetime

# Add ProjectRole enum with numeric values
class ProjectRole(int, enum.Enum):
    MANAGER = 1
    MEMBER = 2
    VIEWER = 3

    @classmethod
    def from_string(cls, role_str: str) -> "ProjectRole":
        role_map = {
            "manager": cls.MANAGER,
            "member": cls.MEMBER,
            "viewer": cls.VIEWER
        }
        return role_map.get(role_str.lower(), cls.MEMBER)

    def to_string(self) -> str:
        role_map = {
            self.MANAGER: "manager",
            self.MEMBER: "member",
            self.VIEWER: "viewer"
        }
        return role_map[self]

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
    role = Column(Enum(ProjectRole, name='projectrole', create_constraint=True, validate_strings=True), default=ProjectRole.MEMBER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships with overlaps parameters
    project = relationship("Project", back_populates="project_members", overlaps="members")
    user = relationship("User", back_populates="project_memberships", overlaps="member_of_projects")

    def __repr__(self):
        return f"<ProjectMember {self.project_id}:{self.user_id}>"

    def has_manager_permissions(self) -> bool:
        """Check if the member has project manager permissions"""
        return self.role == ProjectRole.MANAGER

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
    allow_milestones = Column(Boolean, nullable=False, default=True, comment='Whether milestones are enabled for this project')
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))
    updated_at = Column(DateTime(timezone=True), onupdate=text('now()'))
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_projects")
    project_members = relationship("ProjectMember", back_populates="project", overlaps="members,user")
    members = relationship(
        "User",
        secondary="project_members",
        back_populates="member_of_projects",
        overlaps="project_memberships,project_members,user",
        viewonly=True  # Make this a read-only relationship
    )
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    stages = relationship("TaskStage", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=project_tag, back_populates="projects")
    activities = relationship("Activity", back_populates="project", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="project", cascade="all, delete-orphan")
    stage = relationship("StageDefinition")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_projects")
    time_entries = relationship("TimeEntry", back_populates="project", cascade="all, delete-orphan")
    
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

    # Add new relationships for metrics
    metrics = relationship("ProjectMetrics", back_populates="project", uselist=False)
    resource_metrics = relationship("ResourceMetrics", back_populates="project")

    def calculate_progress(self):
        """Calculate project progress based on task completion."""
        tasks = self.tasks
        if not tasks:
            return 0.0
        return sum(task.progress for task in tasks) / len(tasks)

    def update_metrics(self):
        """Update project metrics based on current state"""
        if not self.metrics:
            from .metrics import ProjectMetrics
            self.metrics = ProjectMetrics(project_id=self.id)
        
        # Calculate schedule variance in hours
        if self.start_date and self.end_date:
            planned_duration = (self.end_date - self.start_date).total_seconds() / 3600  # hours
            actual_duration = (datetime.now() - self.start_date).total_seconds() / 3600  # hours
            self.metrics.schedule_variance = actual_duration - planned_duration
        
        # Calculate milestone completion rate
        total_milestones = len(self.milestones)
        if total_milestones > 0:
            completed_milestones = sum(1 for m in self.milestones if m.is_completed)
            self.metrics.milestone_completion_rate = completed_milestones / total_milestones
        
        # Calculate resource utilization using actual hours
        total_planned_hours = sum(task.planned_hours for task in self.tasks)
        total_actual_hours = sum(
            sum((entry.end_time - entry.start_time).total_seconds() / 3600 
                for entry in task.time_entries 
                if entry.start_time and entry.end_time)
            for task in self.tasks
        )
        if total_planned_hours > 0:
            self.metrics.resource_utilization = total_actual_hours / total_planned_hours
        
        # Calculate team load in hours per person
        active_members = len(self.members)
        if active_members > 0:
            self.metrics.team_load = total_actual_hours / active_members
        
        # Calculate velocity (tasks per week) and throughput
        completed_tasks = sum(1 for task in self.tasks if task.state == 'done')
        total_weeks = max(1, (datetime.now() - self.start_date).total_seconds() / (3600 * 24 * 7)) if self.start_date else 1
        self.metrics.velocity = completed_tasks / total_weeks
        self.metrics.throughput = completed_tasks

    def __repr__(self):
        return f"<Project {self.name}>" 