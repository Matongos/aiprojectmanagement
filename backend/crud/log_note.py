from typing import List, Optional
from sqlalchemy.orm import Session
from models.log_note import LogNote
from models.log_note_attachment import LogNoteAttachment
from models.activity import Activity
from models.task import Task
from schemas.log_note import LogNoteCreate, LogNoteAttachmentCreate
from schemas.activity import ActivityCreate
from fastapi import UploadFile
import os
import uuid
from datetime import datetime

def create_log_note(db: Session, log_note: LogNoteCreate, user_id: int) -> LogNote:
    # Create the log note
    db_log_note = LogNote(
        content=log_note.content,
        task_id=log_note.task_id,
        created_by=user_id
    )
    db.add(db_log_note)
    
    # Get task's project_id for the activity
    task = db.query(Task).filter(Task.id == log_note.task_id).first()
    if task:
        # Create corresponding activity
        activity = Activity(
            activity_type="log_note",  # Using string directly since it's defined in the model
            description=f"Added a log note: {log_note.content[:100]}{'...' if len(log_note.content) > 100 else ''}",
            project_id=task.project_id,
            task_id=log_note.task_id,
            user_id=user_id
        )
        db.add(activity)
    
    db.commit()
    db.refresh(db_log_note)
    return db_log_note

def get_task_log_notes(db: Session, task_id: int, skip: int = 0, limit: int = 100) -> List[LogNote]:
    return db.query(LogNote).filter(
        LogNote.task_id == task_id
    ).order_by(LogNote.created_at.desc()).offset(skip).limit(limit).all()

async def create_log_note_attachment(
    db: Session,
    log_note_id: int,
    file: UploadFile,
    user_id: int,
    upload_dir: str
) -> LogNoteAttachment:
    # Create unique filename
    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    
    # Ensure upload directory exists
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, unique_filename)
    file_content = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Create attachment record
    db_attachment = LogNoteAttachment(
        filename=unique_filename,
        original_filename=file.filename,
        file_size=len(file_content),
        content_type=file.content_type,
        log_note_id=log_note_id,
        uploaded_by=user_id
    )
    
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    return db_attachment

def delete_log_note_attachment(db: Session, attachment_id: int, upload_dir: str) -> bool:
    attachment = db.query(LogNoteAttachment).filter(LogNoteAttachment.id == attachment_id).first()
    if not attachment:
        return False
    
    # Delete file
    file_path = os.path.join(upload_dir, attachment.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete record
    db.delete(attachment)
    db.commit()
    return True 