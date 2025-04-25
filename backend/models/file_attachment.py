from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.base import Base

class FileAttachment(Base):
    __tablename__ = "file_attachments"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    content_type = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Foreign keys
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="attachments")
    user = relationship("User", back_populates="uploaded_files") 