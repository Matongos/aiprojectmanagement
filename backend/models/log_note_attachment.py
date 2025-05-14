from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class LogNoteAttachment(Base):
    __tablename__ = "log_note_attachments"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Foreign keys
    log_note_id = Column(Integer, ForeignKey("log_notes.id", ondelete="CASCADE"))
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    
    # Relationships
    log_note = relationship("LogNote", back_populates="attachments")
    user = relationship("User", back_populates="log_note_attachments") 