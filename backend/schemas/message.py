from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class MessageType(str, Enum):
    TASK_MESSAGE = "task_message"
    DIRECT_MESSAGE = "direct_message"
    SYSTEM_NOTIFICATION = "system_notification"

class UserInfo(BaseModel):
    id: int
    username: str
    full_name: str
    profile_image_url: Optional[str] = None

    class Config:
        from_attributes = True

class TaskInfo(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    """Base model for message schema."""
    content: str = Field(..., min_length=1)
    message_type: MessageType = Field(default=MessageType.TASK_MESSAGE)
    task_id: Optional[int] = None
    recipient_id: Optional[int] = None

class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    pass

class MessageUpdate(BaseModel):
    """Schema for updating a message."""
    is_read: Optional[bool] = None
    content: Optional[str] = Field(None, min_length=1)

class MessageInDB(MessageBase):
    """Schema for message data in the database."""
    id: int
    sender_id: Optional[int]
    is_read: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MessageResponse(MessageBase):
    """Schema for message response."""
    id: int
    sender: Optional[UserInfo] = None
    recipient: Optional[UserInfo] = None
    task: Optional[TaskInfo] = None
    is_read: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 