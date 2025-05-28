from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
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
    
    # AI Analysis Fields
    productivity_score = Column(Float, nullable=True)
    efficiency_metrics = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="time_entries")
    user = relationship("User", back_populates="time_entries")
    project = relationship("Project", back_populates="time_entries")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.start_time and self.end_time:
            self.duration = (self.end_time - self.start_time).total_seconds() / 3600
        elif self.start_time and not self.end_time:
            self.is_running = True
            self.duration = 0

    def stop_timer(self):
        """Stop the running timer and calculate duration"""
        if self.is_running:
            self.end_time = datetime.utcnow()
            self.duration = (self.end_time - self.start_time).total_seconds() / 3600
            self.is_running = False
            return True
        return False

    def update_duration(self):
        """Update duration based on start and end times"""
        if self.start_time and self.end_time:
            self.duration = (self.end_time - self.start_time).total_seconds() / 3600
            return True
        return False

    def calculate_productivity_score(self):
        """AI-assisted productivity score calculation"""
        # This will be implemented with AI integration
        pass

    def __repr__(self):
        return f"<TimeEntry {self.id}: {self.duration} hours>" 