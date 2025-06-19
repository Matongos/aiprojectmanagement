from typing import List, Optional
from sqlalchemy.orm import Session
from models.log_note import LogNote
from models.activity import Activity
from models.task import Task
from schemas.log_note import LogNoteCreate
from schemas.activity import ActivityCreate
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

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
    logger.info(f"Getting log notes for task {task_id} (skip={skip}, limit={limit})")
    try:
        query = db.query(LogNote).filter(LogNote.task_id == task_id)
        logger.debug(f"Base query: {str(query)}")
        
        # Add ordering
        query = query.order_by(LogNote.created_at.desc())
        
        # Add pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        results = query.all()
        logger.info(f"Found {len(results)} log notes")
        return results
    except Exception as e:
        logger.error(f"Error in get_task_log_notes: {str(e)}", exc_info=True)
        raise 