from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
from schemas.log_note import LogNote, LogNoteCreate, LogNoteAttachment
from crud import log_note as log_note_crud
from routers.auth import get_current_user
import os
from config import settings

router = APIRouter(prefix="/log-notes", tags=["log-notes"])

UPLOAD_DIR = os.path.join(settings.UPLOAD_DIR, "log_notes")

@router.post("/", response_model=LogNote)
async def create_log_note(
    content: str = Form(...),
    task_id: int = Form(...),
    files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new log note with optional attachments"""
    # Create log note
    log_note_data = LogNoteCreate(content=content, task_id=task_id)
    log_note = log_note_crud.create_log_note(db, log_note_data, current_user["id"])
    
    # Handle attachments if any
    if files:
        for file in files:
            await log_note_crud.create_log_note_attachment(
                db=db,
                log_note_id=log_note.id,
                file=file,
                user_id=current_user["id"],
                upload_dir=UPLOAD_DIR
            )
    
    # Refresh log note to include attachments
    db.refresh(log_note)
    
    # Add user info to response
    log_note.user = {
        "id": current_user["id"],
        "name": current_user["full_name"] or current_user["username"],
        "avatar": current_user.get("profile_image_url")
    }
    
    return log_note

@router.get("/task/{task_id}", response_model=List[LogNote])
async def get_task_log_notes(
    task_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all log notes for a task"""
    log_notes = log_note_crud.get_task_log_notes(db, task_id, skip, limit)
    
    # Add user info to each log note
    for note in log_notes:
        if note.user:
            note.user = {
                "id": note.user.id,
                "name": note.user.full_name or note.user.username,
                "avatar": note.user.profile_image_url
            }
    
    return log_notes

@router.delete("/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a log note attachment"""
    success = log_note_crud.delete_log_note_attachment(db, attachment_id, UPLOAD_DIR)
    if not success:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return {"message": "Attachment deleted successfully"} 