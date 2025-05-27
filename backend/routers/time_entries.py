from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from database import get_db
from models.time_entry import TimeEntry
from models.task import Task
from models.project import Project
from schemas.time_entry import (
    TimeEntryCreate,
    TimeEntryUpdate,
    TimeEntryInDB,
    TimeEntryWithRelations,
    TimeEntryStats,
    TimeEntryBulkCreate,
    TimeEntryAIInsights
)
from routers.auth import get_current_user
from services.ai_analyzer import analyze_time_entry

router = APIRouter(
    prefix="/time-entries",
    tags=["time-entries"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=TimeEntryInDB)
async def create_time_entry(
    entry: TimeEntryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new time entry"""
    # Verify task exists and user has access
    task = db.query(Task).filter(Task.id == entry.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Create time entry
    db_entry = TimeEntry(**entry.dict())
    db_entry.user_id = current_user["id"]
    
    # If no end time, start timer
    if not entry.end_time:
        db_entry.is_running = True
    
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    
    # Schedule AI analysis
    background_tasks.add_task(analyze_time_entry, db_entry.id)
    
    return db_entry

@router.get("/", response_model=List[TimeEntryWithRelations])
async def get_time_entries(
    skip: int = 0,
    limit: int = 100,
    task_id: Optional[int] = None,
    project_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get time entries with optional filters"""
    query = db.query(TimeEntry).filter(TimeEntry.user_id == current_user["id"])
    
    if task_id:
        query = query.filter(TimeEntry.task_id == task_id)
    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)
    if start_date:
        query = query.filter(TimeEntry.start_time >= start_date)
    if end_date:
        query = query.filter(TimeEntry.start_time <= end_date)
    
    return query.offset(skip).limit(limit).all()

@router.get("/stats", response_model=TimeEntryStats)
async def get_time_entry_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get statistics for time entries"""
    query = db.query(TimeEntry).filter(TimeEntry.user_id == current_user["id"])
    
    if start_date:
        query = query.filter(TimeEntry.start_time >= start_date)
    if end_date:
        query = query.filter(TimeEntry.start_time <= end_date)
    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)
    
    entries = query.all()
    
    total_hours = sum(entry.duration for entry in entries)
    billable_hours = sum(entry.duration for entry in entries if entry.is_billable)
    productivity_scores = [entry.productivity_score for entry in entries if entry.productivity_score]
    
    activity_breakdown = {}
    daily_distribution = {}
    
    for entry in entries:
        # Activity breakdown
        activity = entry.activity_type or "Other"
        activity_breakdown[activity] = activity_breakdown.get(activity, 0) + entry.duration
        
        # Daily distribution
        day = entry.start_time.date().isoformat()
        daily_distribution[day] = daily_distribution.get(day, 0) + entry.duration
    
    return TimeEntryStats(
        total_hours=total_hours,
        billable_hours=billable_hours,
        productivity_average=sum(productivity_scores) / len(productivity_scores) if productivity_scores else 0,
        entries_count=len(entries),
        activity_breakdown=activity_breakdown,
        daily_distribution=daily_distribution
    )

@router.post("/bulk", response_model=List[TimeEntryInDB])
async def create_bulk_time_entries(
    entries: TimeEntryBulkCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create multiple time entries at once"""
    db_entries = []
    for entry in entries.entries:
        db_entry = TimeEntry(**entry.dict())
        db_entry.user_id = current_user["id"]
        db.add(db_entry)
        db_entries.append(db_entry)
    
    db.commit()
    for entry in db_entries:
        db.refresh(entry)
        background_tasks.add_task(analyze_time_entry, entry.id)
    
    return db_entries

@router.put("/{entry_id}", response_model=TimeEntryInDB)
async def update_time_entry(
    entry_id: int,
    entry_update: TimeEntryUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a time entry"""
    db_entry = db.query(TimeEntry).filter(
        TimeEntry.id == entry_id,
        TimeEntry.user_id == current_user["id"]
    ).first()
    
    if not db_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    for field, value in entry_update.dict(exclude_unset=True).items():
        setattr(db_entry, field, value)
    
    if db_entry.start_time and db_entry.end_time:
        db_entry.update_duration()
    
    db.commit()
    db.refresh(db_entry)
    
    # Re-run AI analysis after update
    background_tasks.add_task(analyze_time_entry, db_entry.id)
    
    return db_entry

@router.delete("/{entry_id}")
async def delete_time_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a time entry"""
    db_entry = db.query(TimeEntry).filter(
        TimeEntry.id == entry_id,
        TimeEntry.user_id == current_user["id"]
    ).first()
    
    if not db_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    db.delete(db_entry)
    db.commit()
    
    return {"message": "Time entry deleted"}

@router.post("/{entry_id}/stop", response_model=TimeEntryInDB)
async def stop_time_entry(
    entry_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Stop a running time entry"""
    db_entry = db.query(TimeEntry).filter(
        TimeEntry.id == entry_id,
        TimeEntry.user_id == current_user["id"]
    ).first()
    
    if not db_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    if not db_entry.is_running:
        raise HTTPException(status_code=400, detail="Time entry is not running")
    
    db_entry.stop_timer()
    db.commit()
    db.refresh(db_entry)
    
    # Analyze completed time entry
    background_tasks.add_task(analyze_time_entry, db_entry.id)
    
    return db_entry

@router.get("/{entry_id}/ai-insights", response_model=TimeEntryAIInsights)
async def get_time_entry_ai_insights(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get AI-generated insights for a time entry"""
    db_entry = db.query(TimeEntry).filter(
        TimeEntry.id == entry_id,
        TimeEntry.user_id == current_user["id"]
    ).first()
    
    if not db_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    # Get AI insights
    insights = await analyze_time_entry(entry_id)
    
    return TimeEntryAIInsights(
        entry_id=entry_id,
        productivity_score=db_entry.productivity_score or 0,
        efficiency_metrics=insights.get("efficiency_metrics", {}),
        recommendations=insights.get("recommendations", []),
        patterns=insights.get("patterns", {})
    ) 