from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class TimeEntry(Base):
    """Time entry model for tracking time spent on tasks"""
    __tablename__ = "time_entries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    duration = Column(Float, nullable=False, default=0.0)  # Duration in hours
    description = Column(String, nullable=True)
    activity_type = Column(String(50), nullable=True)
    is_billable = Column(Boolean, default=True)
    is_running = Column(Boolean, default=False)
    
    # Foreign Keys
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="time_entries")
    user = relationship("User", back_populates="time_entries")
    project = relationship("Project", back_populates="time_entries")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.duration is None:
            self.duration = 0.0

    def __repr__(self):
        return f"<TimeEntry {self.id}: {self.duration} hours>" 