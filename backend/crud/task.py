from typing import List, Optional
from sqlalchemy.orm import Session
from models.tasks import Task
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
        self, db: Session, *, status: str, skip: int = 0, limit: int = 100
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
        # Convert Pydantic model to dict
        obj_in_data = obj_in.model_dump()
        
        # Create new Task object
        # Don't include assignee_id in the constructor
        db_obj = self.model(**obj_in_data, created_by=creator_id)
        
        # Add to session, commit and refresh
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
            .filter(Task.due_date < current_date, Task.status != "done")
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_recent_tasks(
        self, db: Session, *, user_id: int, limit: int = 5
    ) -> List[Task]:
        """
        Get the most recently updated tasks for a user.
        This includes both tasks created by the user and assigned to the user.
        """
        return (
            db.query(self.model)
            .filter(
                (Task.created_by == user_id) | (Task.assignee_id == user_id)
            )
            .order_by(Task.updated_at.desc())
            .limit(limit)
            .all()
        )
    
    def get_tasks_over_budget(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """
        Get tasks where the actual hours exceed the estimated hours.
        Only returns tasks that have both estimated_hours and actual_hours set.
        """
        return (
            db.query(self.model)
            .filter(
                Task.estimated_hours.isnot(None),
                Task.actual_hours.isnot(None),
                Task.actual_hours > Task.estimated_hours
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

task = CRUDTask(Task) 