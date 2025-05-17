from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_
from models.project import Project
from models.task import Task
from models.task_stage import TaskStage
from schemas.project import ProjectCreate, ProjectUpdate
from schemas.task_stage import TaskStageCreate
from crud.base import CRUDBase
import string
import random
from datetime import datetime

class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    def get_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        return (
            db.query(Project)
            .options(joinedload(Project.tasks))
            .filter(Project.created_by == owner_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_status(
        self, db: Session, *, status: str, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        return (
            db.query(Project)
            .options(joinedload(Project.tasks))
            .filter(Project.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_active(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        return (
            db.query(Project)
            .options(joinedload(Project.tasks))
            .filter(Project.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def _generate_key(self, name: str) -> str:
        """Generate a unique project key based on the project name."""
        # Extract first letters of each word
        words = name.split()
        key_base = ''.join([word[0].upper() for word in words if word])
        if not key_base:
            key_base = 'PROJ'
        
        # Add some random characters
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        return (key_base[:5] + random_chars)[:10]
    
    def create_with_owner(
        self, db: Session, *, obj_in: ProjectCreate, owner_id: int
    ) -> Project:
        # Get fields from ProjectCreate
        obj_data = obj_in.model_dump(exclude_unset=True)
        
        # If key is not provided, generate one
        if 'key' not in obj_data or not obj_data['key']:
            obj_data['key'] = self._generate_key(obj_in.name)
        
        # Create project with creator
        db_obj = Project(
            **obj_data,
            created_by=owner_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        # Create default stages
        default_stages = [
            {"name": "Inbox", "description": "Default stage for unorganized tasks", "sequence": 1}
        ]

        for stage_data in default_stages:
            stage = TaskStage(
                project_id=db_obj.id,
                **stage_data
            )
            db.add(stage)
        
        db.commit()
        return db_obj

    def get_recent_projects(
        self, db: Session, *, user_id: int, limit: int = 5
    ) -> List[Project]:
        """
        Get the most recently updated projects for a specific user.
        """
        return (
            db.query(Project)
            .options(joinedload(Project.tasks))
            .filter(Project.created_by == user_id)
            .order_by(desc(Project.updated_at))
            .limit(limit)
            .all()
        )
        
    def search_projects(
        self, db: Session, *, user_id: int, query: str, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        """
        Search for projects by name, key, or description.
        Results are filtered to only include projects created by the user.
        """
        search_query = f"%{query}%"
        return (
            db.query(self.model)
            .filter(Project.created_by == user_id)
            .filter(
                or_(
                    Project.name.ilike(search_query),
                    Project.key.ilike(search_query),
                    Project.description.ilike(search_query)
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_tags(self, db: Session) -> List[str]:
        """Get all unique tags from all projects"""
        projects = db.query(self.model).all()
        all_tags = set()
        for project in projects:
            if project.tags:
                all_tags.update(project.tags)
        return sorted(list(all_tags))

class CRUDProjectStage(CRUDBase[TaskStage, TaskStageCreate, TaskStageCreate]):
    def create_stage(self, db: Session, *, obj_in: TaskStageCreate) -> TaskStage:
        db_obj = TaskStage(
            name=obj_in.name,
            description=obj_in.description,
            project_id=obj_in.project_id,
            sequence=obj_in.sequence
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_project_stages(self, db: Session, *, project_id: int) -> List[TaskStage]:
        return db.query(TaskStage).filter(TaskStage.project_id == project_id).order_by(TaskStage.sequence).all()

    def update_stage_progress(self, db: Session, *, stage_id: int) -> TaskStage:
        stage = db.query(TaskStage).filter(TaskStage.id == stage_id).first()
        if stage:
            stage.update_progress()
            db.commit()
            db.refresh(stage)
        return stage

project = CRUDProject(Project)
project_stage = CRUDProjectStage(TaskStage) 