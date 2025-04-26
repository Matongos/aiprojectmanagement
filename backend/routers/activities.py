from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from crud import activity as crud
from schemas.activity import Activity as ActivitySchema, ActivityCreate, ActivityUpdate
from database import get_db
from routers.auth import get_current_user

router = APIRouter(
    prefix="/activities",
    tags=["activities"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[ActivitySchema])
async def read_activities(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a list of all recent activities."""
    activities = crud.get_activities_by_user(db, current_user["id"], skip=skip, limit=limit)
    return [crud.get_activity_with_user_data(db, activity) for activity in activities]


@router.get("/project/{project_id}", response_model=List[ActivitySchema])
async def read_project_activities(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all activities for a specific project."""
    activities = crud.get_activities_by_project(db, project_id, skip=skip, limit=limit)
    return [crud.get_activity_with_user_data(db, activity) for activity in activities]


@router.get("/task/{task_id}", response_model=List[ActivitySchema])
async def read_task_activities(
    task_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all activities for a specific task."""
    activities = crud.get_activities_by_task(db, task_id, skip=skip, limit=limit)
    return [crud.get_activity_with_user_data(db, activity) for activity in activities]


@router.get("/user/{user_id}", response_model=List[ActivitySchema])
async def read_user_activities(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all activities for a specific user."""
    activities = crud.get_activities_by_user(db, user_id, skip=skip, limit=limit)
    return [crud.get_activity_with_user_data(db, activity) for activity in activities]


@router.post("/", response_model=ActivitySchema)
async def create_activity(
    activity: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new activity."""
    # Override the user_id with the current user's ID
    activity_data = activity.dict()
    activity_data["user_id"] = current_user["id"]
    
    db_activity = crud.create_activity(db, ActivityCreate(**activity_data))
    return crud.get_activity_with_user_data(db, db_activity) 