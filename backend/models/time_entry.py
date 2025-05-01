from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class TimeEntry(Base):
    __tablename__ = "time_entries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    hours = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    
    # Foreign Keys
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="time_entries")
    user = relationship("User", back_populates="time_entries")
    
    # Timestamps
    date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<TimeEntry {self.id}: {self.hours} hours>" 