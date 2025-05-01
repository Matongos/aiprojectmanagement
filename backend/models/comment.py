from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    
    # Foreign Keys
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="comments")
    project = relationship("Project", back_populates="comments")
    author = relationship("User", back_populates="comments")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Comment {self.id}>" 