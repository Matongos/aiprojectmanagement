from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime

class LogNoteAttachmentBase(BaseModel):
    original_filename: str
    file_size: int
    content_type: str

class LogNoteAttachmentCreate(LogNoteAttachmentBase):
    pass

class LogNoteAttachment(LogNoteAttachmentBase):
    id: int
    filename: str
    log_note_id: int
    uploaded_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class LogNoteBase(BaseModel):
    content: str

class LogNoteCreate(LogNoteBase):
    task_id: int

class UserInfo(BaseModel):
    id: int
    username: str
    full_name: str
    profile_image_url: Optional[str] = None

class LogNoteResponse(LogNoteBase):
    id: int
    task_id: int
    created_by: Optional[int]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    attachments: List[LogNoteAttachment] = []
    user: Optional[Dict] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat() if dt else None
        }

class LogNote(LogNoteBase):
    id: int
    task_id: int
    created_by: Optional[int]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    attachments: List[LogNoteAttachment] = []
    user: Optional[UserInfo] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat() if dt else None
        } 