from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class NotificationBase(BaseModel):
    """Base model for notification schema."""
    title: str
    content: Optional[str] = None
    type: str
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    user_id: int

class NotificationCreate(NotificationBase):
    """Schema for creating a new notification."""
    pass

class NotificationUpdate(BaseModel):
    """Schema for updating a notification."""
    is_read: Optional[bool] = None
    title: Optional[str] = None
    content: Optional[str] = None

class NotificationInDB(NotificationBase):
    """Schema for notification data in the database."""
    id: int
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Notification(NotificationInDB):
    """Schema for notification data returned to the client."""
    pass 