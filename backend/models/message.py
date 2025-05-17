from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
import enum

class MessageType(str, enum.Enum):
    TASK_MESSAGE = "task_message"
    DIRECT_MESSAGE = "direct_message"
    SYSTEM_NOTIFICATION = "system_notification"

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    message_type = Column(Enum(MessageType), nullable=False, default=MessageType.TASK_MESSAGE)
    
    # Sender information
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Task reference (optional - for messages in tasks)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    
    # For direct messages between users
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    task = relationship("Task", back_populates="messages")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")
    
    # Message metadata
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Message {self.id}: from {self.sender_id} to {self.recipient_id or f'task {self.task_id}'}>" 