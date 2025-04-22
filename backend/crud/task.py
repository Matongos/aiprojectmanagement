from typing import List, Optional
from sqlalchemy.orm import Session
from models.task import Task, TaskStatus
from schemas.task import TaskCreate, TaskUpdate
from crud.base import CRUDBase

class CRUDTask(CRUDBase[Task, TaskCreate, TaskUpdate]):
    def get_by_project(
        self, db: Session, *, project_id: int, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        return (
            db.query(self.model)
            .filter(Task.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_status(
        self, db: Session, *, status: TaskStatus, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        return (
            db.query(self.model)
            .filter(Task.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_assignee(
        self, db: Session, *, assignee_id: int, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        return (
            db.query(self.model)
            .filter(Task.assignee_id == assignee_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_with_creator(
        self, db: Session, *, obj_in: TaskCreate, creator_id: int
    ) -> Task:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data, creator_id=creator_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_tasks_by_priority(
        self, db: Session, *, priority: str, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        return (
            db.query(self.model)
            .filter(Task.priority == priority)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_overdue_tasks(
        self, db: Session, *, current_date, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        return (
            db.query(self.model)
            .filter(Task.due_date < current_date, Task.status != TaskStatus.DONE)
            .offset(skip)
            .limit(limit)
            .all()
        )

task = CRUDTask(Task) 