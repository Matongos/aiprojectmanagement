from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.task import Task
from models.user import User
from schemas.task import TaskState
from fastapi import HTTPException

class ScheduledTaskService:
    @staticmethod
    def update_task_states(db: Session):
        """
        Check and update task states based on scheduled start dates.
        This should be run periodically (e.g., every minute) to check for tasks
        that need to transition to IN_PROGRESS.
        """
        current_time = datetime.utcnow()
        
        # Find tasks that should transition to IN_PROGRESS
        tasks_to_update = db.query(Task).filter(
            and_(
                Task.state == TaskState.NULL,
                Task.start_date <= current_time,
                Task.start_date.isnot(None)
            )
        ).all()
        
        # Update task states
        for task in tasks_to_update:
            task.state = TaskState.IN_PROGRESS
            db.add(task)
        
        if tasks_to_update:
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to update task states: {str(e)}"
                )

    @staticmethod
    def can_set_start_date(db: Session, user_id: int, project_id: int) -> bool:
        """
        Check if a user has permission to set task start dates.
        Returns True if user is a superuser or project manager.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
            
        # Superusers can always set start dates
        if user.is_superuser:
            return True
            
        # Check if user is project manager
        project_role = db.query("project_members").filter(
            and_(
                "project_members.project_id" == project_id,
                "project_members.user_id" == user_id,
                "project_members.role" == "manager"
            )
        ).first()
        
        return project_role is not None 