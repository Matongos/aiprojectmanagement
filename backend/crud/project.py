from typing import List, Optional
from sqlalchemy.orm import Session
from models.project import Project, ProjectStatus
from schemas.project import ProjectCreate, ProjectUpdate
from crud.base import CRUDBase

class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    def get_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        return (
            db.query(self.model)
            .filter(Project.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_status(
        self, db: Session, *, status: ProjectStatus, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        return (
            db.query(self.model)
            .filter(Project.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_active(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        return (
            db.query(self.model)
            .filter(Project.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_with_owner(
        self, db: Session, *, obj_in: ProjectCreate, owner_id: int
    ) -> Project:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data, owner_id=owner_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

project = CRUDProject(Project) 