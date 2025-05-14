from typing import List, Optional
from pydantic import BaseModel
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

class LogNote(LogNoteBase):
    id: int
    task_id: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    attachments: List[LogNoteAttachment] = []
    user: Optional[dict] = None  # Will include user details like name and avatar

    class Config:
        from_attributes = True 