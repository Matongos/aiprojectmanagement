from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from database import get_db
from models.time_entry import TimeEntry
from schemas.time_entry import TimeEntryCreate, TimeEntryUpdate, TimeEntryResponse
from routers.auth import get_current_user

router = APIRouter(
    prefix="/time-entries",
    tags=["time-entries"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=TimeEntryResponse)
async def create_time_entry(
    time_entry: TimeEntryCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new time entry"""
    db_time_entry = TimeEntry(
        hours=time_entry.hours,
        description=time_entry.description,
        task_id=time_entry.task_id,
        user_id=current_user["id"],
        date=time_entry.date or datetime.utcnow()
    )
    db.add(db_time_entry)
    db.commit()
    db.refresh(db_time_entry)
    return db_time_entry

@router.get("/", response_model=List[TimeEntryResponse])
async def read_time_entries(
    task_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get time entries with optional task filtering"""
    query = db.query(TimeEntry)
    
    # Filter by task if specified
    if task_id is not None:
        query = query.filter(TimeEntry.task_id == task_id)
    
    # Regular users can only see their own time entries
    if not current_user.get("is_superuser"):
        query = query.filter(TimeEntry.user_id == current_user["id"])
    
    return query.offset(skip).limit(limit).all()

@router.get("/{time_entry_id}", response_model=TimeEntryResponse)
async def read_time_entry(
    time_entry_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific time entry"""
    time_entry = db.query(TimeEntry).filter(TimeEntry.id == time_entry_id).first()
    if not time_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    # Check permissions
    if not current_user.get("is_superuser") and time_entry.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return time_entry

@router.put("/{time_entry_id}", response_model=TimeEntryResponse)
async def update_time_entry(
    time_entry_id: int,
    time_entry: TimeEntryUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a time entry"""
    db_time_entry = db.query(TimeEntry).filter(TimeEntry.id == time_entry_id).first()
    if not db_time_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    # Check permissions
    if not current_user.get("is_superuser") and db_time_entry.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Update fields
    for field, value in time_entry.model_dump(exclude_unset=True).items():
        setattr(db_time_entry, field, value)
    
    db.commit()
    db.refresh(db_time_entry)
    return db_time_entry

@router.delete("/{time_entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_time_entry(
    time_entry_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a time entry"""
    time_entry = db.query(TimeEntry).filter(TimeEntry.id == time_entry_id).first()
    if not time_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    # Check permissions
    if not current_user.get("is_superuser") and time_entry.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db.delete(time_entry)
    db.commit() 