from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base

class Milestone(Base):
    """Milestone model for project management"""
    __tablename__ = "milestones"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    is_completed = Column(Boolean, default=False)
    
    # Foreign Keys
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="milestones")
    tasks = relationship("Task", back_populates="milestone")
    creator = relationship("User", back_populates="created_milestones")

    def __repr__(self):
        return f"<Milestone {self.name}>" 