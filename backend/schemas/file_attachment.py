from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class FileAttachmentBase(BaseModel):
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    description: Optional[str] = None

class FileAttachmentCreate(FileAttachmentBase):
    task_id: int

class FileAttachmentUpdate(BaseModel):
    description: Optional[str] = None

class FileAttachmentInDB(FileAttachmentBase):
    id: int
    file_path: str
    task_id: int
    uploaded_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class FileAttachment(FileAttachmentInDB):
    pass 