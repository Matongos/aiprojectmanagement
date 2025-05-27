from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime, timedelta

from ..dependencies import get_db
from services.metrics_collector import MetricsCollector
from services.event_handlers import MetricsEventHandler

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/project/{project_id}")
async def get_project_metrics(
    project_id: int,
    time_range: str = "7d",  # Options: 24h, 7d, 30d, all
    db: Session = Depends(get_db)
):
    """Get project metrics for specified time range"""
    try:
        # Calculate time range
        end_date = datetime.utcnow()
        if time_range == "24h":
            start_date = end_date - timedelta(days=1)
        elif time_range == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_range == "30d":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = None

        # Query metrics
        metrics = await _get_project_metrics(db, project_id, start_date, end_date)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}")
async def get_task_metrics(
    task_id: int,
    db: Session = Depends(get_db)
):
    """Get task metrics"""
    try:
        metrics = await _get_task_metrics(db, task_id)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/resource/{user_id}")
async def get_resource_metrics(
    user_id: int,
    project_id: int = None,
    time_range: str = "7d",
    db: Session = Depends(get_db)
):
    """Get resource metrics, optionally filtered by project"""
    try:
        # Calculate time range
        end_date = datetime.utcnow()
        if time_range == "24h":
            start_date = end_date - timedelta(days=1)
        elif time_range == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_range == "30d":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = None

        metrics = await _get_resource_metrics(db, user_id, project_id, start_date, end_date)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/collect/project/{project_id}")
async def trigger_project_metrics_collection(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Manually trigger project metrics collection"""
    try:
        collector = MetricsCollector(db)
        success = await collector.collect_project_metrics(project_id)
        if success:
            return {"message": "Project metrics collected successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to collect project metrics")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions for querying metrics
async def _get_project_metrics(
    db: Session,
    project_id: int,
    start_date: datetime = None,
    end_date: datetime = None
) -> Dict:
    """Query project metrics from database"""
    # Implementation to fetch project metrics
    pass

async def _get_task_metrics(
    db: Session,
    task_id: int
) -> Dict:
    """Query task metrics from database"""
    # Implementation to fetch task metrics
    pass

async def _get_resource_metrics(
    db: Session,
    user_id: int,
    project_id: int = None,
    start_date: datetime = None,
    end_date: datetime = None
) -> Dict:
    """Query resource metrics from database"""
    # Implementation to fetch resource metrics
    pass 