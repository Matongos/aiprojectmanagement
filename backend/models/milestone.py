from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base

class Milestone(Base):
    """Milestone model for project management"""
    __tablename__ = "milestones"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "First Phase", "Second Phase", "Final Phase"
    description = Column(Text, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    due_date = Column(Date, nullable=True)
    completed_date = Column(Date, nullable=True)
    is_completed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="milestones")
    creator = relationship("User", foreign_keys=[created_by])
    tasks = relationship("Task", back_populates="milestone")

    def __repr__(self):
        return f"<Milestone {self.name}>" 