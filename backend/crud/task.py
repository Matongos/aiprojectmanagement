from typing import List, Optional
from sqlalchemy.orm import Session
from models.task import Task
from schemas.task import TaskCreate, TaskUpdate, TaskState
from crud.base import CRUDBase
from sqlalchemy import or_

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
    
    def get_tasks_by_state(
        self, db: Session, *, state: TaskState, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        return (
            db.query(self.model)
            .filter(Task.state == state)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_assignee(
        self, db: Session, *, assignee_id: int, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        return (
            db.query(self.model)
            .filter(Task.assigned_to == assignee_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_user_tasks(
        self, db: Session, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Get all tasks assigned to or created by a user"""
        return (
            db.query(self.model)
            .filter(
                or_(
                    Task.assigned_to == user_id,
                    Task.created_by == user_id
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_with_creator(
        self, db: Session, *, obj_in: TaskCreate, creator_id: int
    ) -> Task:
        # Convert Pydantic model to dict
        obj_in_data = obj_in.model_dump()
        
        # Create new Task object with default state
        db_obj = self.model(**obj_in_data, created_by=creator_id, state=TaskState.IN_PROGRESS)
        
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
            .filter(Task.deadline < current_date, Task.state != TaskState.DONE)
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
                (Task.created_by == user_id) | (Task.assigned_to == user_id)
            )
            .order_by(Task.updated_at.desc())
            .limit(limit)
            .all()
        )
    
    def get_tasks_over_budget(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """
        Get tasks where the planned hours are exceeded.
        Only returns tasks that have planned_hours set.
        """
        return (
            db.query(self.model)
            .filter(
                Task.planned_hours.isnot(None),
                Task.progress > 100
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_state(
        self, db: Session, *, db_obj: Task, state: TaskState
    ) -> Task:
        """Update a task's state"""
        db_obj.state = state
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_tasks_by_stage(
        self, db: Session, *, stage_id: int, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Get all tasks in a specific stage"""
        return (
            db.query(self.model)
            .filter(Task.stage_id == stage_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

def create_task(db: Session, *, obj_in: TaskCreate, created_by: int) -> Task:
    """Create a new task"""
    # Convert depends_on_ids to actual task objects
    depends_on = []
    if obj_in.depends_on_ids:
        depends_on = db.query(Task).filter(Task.id.in_(obj_in.depends_on_ids)).all()
    
    # Create task object with NULL as default state
    db_obj = Task(
        **obj_in.model_dump(exclude={'depends_on_ids'}),
        created_by=created_by,
        state=TaskState.NULL
    )
    
    # Add dependencies
    if depends_on:
        db_obj.depends_on.extend(depends_on)
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_task(db: Session, task_id: int) -> Optional[Task]:
    """Get a task by ID"""
    return db.query(Task).filter(Task.id == task_id).first()

def get_project_tasks(
    db: Session, 
    project_id: int, 
    skip: int = 0, 
    limit: int = 100
) -> List[Task]:
    """Get all tasks for a project"""
    return db.query(Task)\
        .filter(Task.project_id == project_id)\
        .offset(skip)\
        .limit(limit)\
        .all()

def update_task(db: Session, *, db_obj: Task, obj_in: TaskUpdate) -> Task:
    """Update a task"""
    update_data = obj_in.model_dump(exclude_unset=True)
    
    # Handle dependencies separately
    depends_on_ids = update_data.pop('depends_on_ids', None)
    if depends_on_ids is not None:
        depends_on = db.query(Task).filter(Task.id.in_(depends_on_ids)).all()
        db_obj.depends_on = depends_on
    
    # Update other fields
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_task(db: Session, *, task_id: int) -> Task:
    """Delete a task"""
    obj = db.query(Task).get(task_id)
    db.delete(obj)
    db.commit()
    return obj

def search_tasks(
    db: Session, 
    project_id: Optional[int] = None,
    search_term: str = "",
    skip: int = 0, 
    limit: int = 100
) -> List[Task]:
    """Search tasks by name or description"""
    query = db.query(Task)
    
    if project_id:
        query = query.filter(Task.project_id == project_id)
    
    if search_term:
        search = f"%{search_term}%"
        query = query.filter(
            or_(
                Task.name.ilike(search),
                Task.description.ilike(search)
            )
        )
    
    return query.offset(skip).limit(limit).all()

def get_tasks_by_stage(
    db: Session, 
    stage_id: int,
    skip: int = 0, 
    limit: int = 100
) -> List[Task]:
    """Get all tasks in a stage"""
    return db.query(Task)\
        .filter(Task.stage_id == stage_id)\
        .offset(skip)\
        .limit(limit)\
        .all()

task = CRUDTask(Task) 