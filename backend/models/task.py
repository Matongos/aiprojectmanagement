from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="to-do")
    priority = Column(String, nullable=False, default="medium")
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Foreign keys
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    stage_id = Column(Integer, ForeignKey("task_stages.id"), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    user = relationship("User", back_populates="tasks")
    activities = relationship("Activity", back_populates="task")
    stage = relationship("TaskStage", back_populates="tasks") 