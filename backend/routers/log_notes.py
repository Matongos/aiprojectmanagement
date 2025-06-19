from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from database import get_db
from schemas.log_note import LogNote, LogNoteCreate, LogNoteResponse
from crud import log_note as log_note_crud
from routers.auth import get_current_user
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/log-notes", tags=["log-notes"])

@router.post("/", response_model=LogNoteResponse)
async def create_log_note(
    content: str = Form(...),
    task_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new log note"""
    try:
        # Create log note
        log_note_data = LogNoteCreate(content=content, task_id=task_id)
        log_note = log_note_crud.create_log_note(db, log_note_data, current_user["id"])
        
        # Set timestamps
        current_time = datetime.utcnow()
        log_note.created_at = current_time
        log_note.updated_at = current_time
        
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
        logger.debug(f"Current user: {current_user.get('username')}")
        log_notes = log_note_crud.get_task_log_notes(db, task_id, skip, limit)
        logger.info(f"Found {len(log_notes)} log notes")
        
        # Convert to response models
        response = [
            LogNoteResponse(
                id=note.id,
                content=note.content,
                task_id=note.task_id,
                created_by=note.created_by,
                created_at=note.created_at or datetime.utcnow(),
                updated_at=note.updated_at or datetime.utcnow(),
                user={
                    "id": note.user.id,
                    "username": note.user.username,
                    "full_name": note.user.full_name,
                    "profile_image_url": note.user.profile_image_url
                } if note.user else None
            )
            for note in log_notes
        ]
        logger.info("Successfully converted log notes to response format")
        return response
    except Exception as e:
        logger.error(f"Error fetching log notes: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch log notes: {str(e)}"
        ) 