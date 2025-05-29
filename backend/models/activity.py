from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

from .base import Base


class ActivityType(str, Enum):
    """Enum for activity types."""
    TASK_UPDATE = "task_update"
    COMMENT = "comment"
    LOG_NOTE = "log_note"
    MESSAGE = "message"
    SYSTEM_NOTIFICATION = "system_notification"


class Activity(Base):
    """Database model for activities."""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    activity_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Foreign keys
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="activities")
    task = relationship("Task", back_populates="activities")
    user = relationship("User", back_populates="activities") 