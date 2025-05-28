from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.milestone import Milestone
from models.project import Project
from schemas.milestone import MilestoneCreate, MilestoneUpdate, MilestoneResponse
from routers.auth import get_current_user

router = APIRouter(
    prefix="/milestones",
    tags=["milestones"],
    dependencies=[Depends(get_current_user)]
)

def check_milestones_enabled(project_id: int, db: Session):
    """Check if milestones are enabled for the project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.allow_milestones:
        raise HTTPException(status_code=403, detail="Milestones are not enabled for this project")
    return project

@router.post("/", response_model=MilestoneResponse)
async def create_milestone(
    milestone: MilestoneCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new milestone"""
    # Check if milestones are enabled
    check_milestones_enabled(milestone.project_id, db)
    
    db_milestone = Milestone(
        name=milestone.name,
        description=milestone.description,
        project_id=milestone.project_id,
        due_date=milestone.due_date,
        completed_date=milestone.completed_date,
        is_completed=milestone.is_completed,
        is_active=milestone.is_active,
        created_by=current_user["id"]
    )
    db.add(db_milestone)
    db.commit()
    db.refresh(db_milestone)
    return db_milestone

@router.get("/project/{project_id}", response_model=List[MilestoneResponse])
async def get_project_milestones(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all milestones for a project"""
    # Check if milestones are enabled
    check_milestones_enabled(project_id, db)
    
    milestones = db.query(Milestone).filter(
        Milestone.project_id == project_id,
        Milestone.is_active == True
    ).order_by(Milestone.created_at.desc()).all()
    return milestones

@router.put("/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    milestone_id: int,
    milestone: MilestoneUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a milestone"""
    db_milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not db_milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    # Check if milestones are enabled
    check_milestones_enabled(db_milestone.project_id, db)
    
    for field, value in milestone.model_dump(exclude_unset=True).items():
        setattr(db_milestone, field, value)
    
    db.commit()
    db.refresh(db_milestone)
    return db_milestone

@router.delete("/{milestone_id}")
async def delete_milestone(
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a milestone"""
    db_milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not db_milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    db_milestone.is_active = False
    db.commit()
    return {"message": "Milestone deleted successfully"} 