from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, text, Text, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import List

from .base import Base
from .message import Message
from .task import task_followers
from .project import project_followers
from .metrics import ResourceMetrics

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    profile_image_url = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    email_notifications_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))
    updated_at = Column(DateTime(timezone=True), onupdate=text('now()'))

    # New fields for expertise and notes
    profession = Column(String, nullable=True)
    expertise = Column(ARRAY(String), nullable=True)
    skills = Column(ARRAY(String), nullable=True)
    experience_level = Column(String, nullable=True)  # junior, mid, senior, expert
    notes = Column(Text, nullable=True)
    certifications = Column(ARRAY(String), nullable=True)
    preferred_working_hours = Column(String, nullable=True)
    specializations = Column(ARRAY(String), nullable=True)
    
    # Relationships using string references to avoid circular imports
    roles = relationship("Role", secondary="user_role", back_populates="users", lazy="joined")
    assigned_tasks = relationship("Task", foreign_keys="Task.assigned_to", back_populates="assignee")
    created_tasks = relationship("Task", foreign_keys="Task.created_by", back_populates="creator")
    created_projects = relationship("Project", foreign_keys="Project.created_by", back_populates="creator")
    created_milestones = relationship("Milestone", foreign_keys="Milestone.created_by", back_populates="creator")
    created_companies = relationship("Company", foreign_keys="Company.created_by", back_populates="creator", overlaps="creator")
    project_memberships = relationship("ProjectMember", back_populates="user", overlaps="member_of_projects")
    time_entries = relationship("TimeEntry", back_populates="user")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user")
    uploaded_files = relationship("FileAttachment", back_populates="user")
    activities = relationship("Activity", back_populates="user")
    log_notes = relationship("LogNote", back_populates="user")
    log_note_attachments = relationship("LogNoteAttachment", back_populates="user")
    
    # Message relationships
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.recipient_id", back_populates="recipient")

    # Task relationships
    followed_tasks = relationship("Task", secondary=task_followers, back_populates="followers")

    # Project relationships
    followed_projects = relationship("Project", secondary=project_followers, back_populates="followers")

    # New relationships
    owned_projects = relationship(
        "Project",
        primaryjoin="User.id==Project.owner_id",
        back_populates="owner"
    )
    member_of_projects = relationship(
        "Project",
        secondary="project_members",
        back_populates="members",
        overlaps="project_memberships,project_members,project",
        viewonly=True
    )
    metrics = relationship("ResourceMetrics", back_populates="user")

    def __repr__(self):
        return f"<User {self.username}>" 