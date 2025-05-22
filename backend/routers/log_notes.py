from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
from schemas.log_note import LogNote, LogNoteCreate, LogNoteAttachment, LogNoteResponse
from crud import log_note as log_note_crud
from routers.auth import get_current_user
import os
from config import settings
from sqlalchemy import func

router = APIRouter(prefix="/log-notes", tags=["log-notes"])

UPLOAD_DIR = os.path.join(settings.UPLOAD_DIR, "log_notes")
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Ensure upload directory exists

@router.post("/", response_model=LogNoteResponse)
async def create_log_note(
    content: str = Form(...),
    task_id: int = Form(...),
    files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new log note."""
    try:
        # Create log note
        log_note_data = LogNoteCreate(content=content, task_id=task_id)
        log_note = log_note_crud.create_log_note(db, log_note_data, current_user["id"])
        
        # Handle attachments if any
        if files:  # Only process files if they exist
            for file in files:
                if file and file.filename and not isinstance(file, str):  # Ensure it's a valid UploadFile
                    await log_note_crud.create_log_note_attachment(
                        db=db,
                        log_note_id=log_note.id,
                        file=file,
                        user_id=current_user["id"],
                        upload_dir=UPLOAD_DIR
                    )
        
        # Save changes to database
        db.commit()
        db.refresh(log_note)
        
        # Convert to response model
        return LogNoteResponse(
            id=log_note.id,
            content=log_note.content,
            task_id=log_note.task_id,
            created_by=log_note.created_by,
            created_at=log_note.created_at,
            updated_at=log_note.updated_at,
            attachments=log_note.attachments,
            user={
                "id": current_user["id"],
                "username": current_user["username"],
                "full_name": current_user["full_name"],
                "profile_image_url": current_user.get("profile_image_url")
            }
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create log note: {str(e)}"
        )

@router.get("/task/{task_id}", response_model=List[LogNoteResponse])
async def get_task_log_notes(
    task_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all log notes for a task"""
    try:
        log_notes = log_note_crud.get_task_log_notes(db, task_id, skip, limit)
        
        # Convert to response models
        return [
            LogNoteResponse(
                id=note.id,
                content=note.content,
                task_id=note.task_id,
                created_by=note.created_by,
                created_at=note.created_at,
                updated_at=note.updated_at,
                attachments=note.attachments,
                user={
                    "id": note.user.id,
                    "username": note.user.username,
                    "full_name": note.user.full_name,
                    "profile_image_url": note.user.profile_image_url
                } if note.user else None
            )
            for note in log_notes
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch log notes: {str(e)}"
        )

@router.delete("/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a log note attachment"""
    try:
        success = log_note_crud.delete_log_note_attachment(db, attachment_id, UPLOAD_DIR)
        if not success:
            raise HTTPException(status_code=404, detail="Attachment not found")
        return {"message": "Attachment deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete attachment: {str(e)}"
        ) 