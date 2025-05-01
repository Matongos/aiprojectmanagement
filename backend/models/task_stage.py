from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class TaskStage(Base):
    """Task Stage model for project management"""
    __tablename__ = "task_stages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sequence = Column(Integer, nullable=False, server_default='1')  # For ordering stages
    is_active = Column(Boolean, default=True)
    fold = Column(Boolean, default=False)  # Whether stage is folded (e.g. done/canceled)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    auto_progress_percentage = Column(Float, default=0.0)  # Auto-set progress when task enters stage
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="stages")
    tasks = relationship("Task", back_populates="stage", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TaskStage {self.name}>"

    def get_tasks(self):
        """Get all tasks in this stage"""
        return self.tasks

    def get_active_tasks(self):
        """Get active tasks in this stage"""
        return [task for task in self.tasks if task.is_active]

    def get_task_count(self):
        """Get number of tasks in this stage"""
        return len(self.tasks)

    def move_task_to_stage(self, task, new_stage):
        """Move a task from this stage to another"""
        if task in self.tasks:
            task.stage = new_stage
            task.date_last_stage_update = func.now()
            return True
        return False 