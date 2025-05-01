from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)  # e.g., 'task_assignment', 'mention', etc.
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