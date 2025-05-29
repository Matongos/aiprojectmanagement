from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from .base import Base


class NotificationType(str, Enum):
    """Enum for notification types."""
    TASK_ASSIGNMENT = "task_assignment"
    TASK_UPDATE = "task_update"
    TASK_COMMENT = "task_comment"
    TASK_MENTION = "task_mention"
    MESSAGE = "message"
    PROJECT_UPDATE = "project_update"
    MILESTONE_UPDATE = "milestone_update"
    SYSTEM = "system"
    DEADLINE_REMINDER = "deadline_reminder"
    LOG_NOTE = "log_note"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)  # Changed to nullable=True to match schema
    type = Column(String(50), nullable=False)  # Changed from notification_type to type
    is_read = Column(Boolean, default=False)
    
    # Reference info (e.g., task_id if notification is about a task)
    reference_type = Column(String(50), nullable=True)  # e.g., 'task', 'project', etc.
    reference_id = Column(Integer, nullable=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Notification {self.id}: {self.title}>" 