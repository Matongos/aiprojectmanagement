from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, time
from models.task import Task
from models.project import Project
from models.task_stage import TaskStage
from models.metrics import TaskMetrics
from schemas.task import TaskCreate, TaskState
from .permission_service import PermissionService
from .scheduled_tasks import ScheduledTaskService
from workers.metrics_worker import metrics_worker
from fastapi import HTTPException
from sqlalchemy.sql import func

class TaskService:
    def __init__(self):
        self.permission_service = PermissionService()

    @staticmethod
    def get_next_workday_8am(from_date: datetime) -> datetime:
        """Get the next workday at 8am from a given date"""
        # Set time to 8am
        next_day = from_date.replace(hour=8, minute=0, second=0, microsecond=0)
        
        # If it's already past 8am, move to next day
        if from_date.time() >= time(8, 0):
            next_day += timedelta(days=1)
        
        # Skip weekends
        while next_day.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
            next_day += timedelta(days=1)
        
        return next_day

    def create_task(
        self,
        db: Session,
        task_data: TaskCreate,
        current_user_id: int
    ) -> Task:
        """Create a new task with default values for optional fields"""
        # Check project permissions if project_id is provided
        if task_data.project_id:
            if not self.permission_service.can_modify_project(db, current_user_id, task_data.project_id):
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to create tasks in this project"
                )
            
            # Get project deadline
            project = db.query(Project).filter(Project.id == task_data.project_id).first()
            if project and project.end_date and task_data.deadline:
                task_deadline = task_data.deadline
                if task_deadline > project.end_date:
                    raise HTTPException(
                        status_code=400,
                        detail="Task deadline cannot exceed project deadline"
                    )

        # Convert task data to dict and remove tag_ids
        task_dict = task_data.dict()
        
        # Remove fields that are not in the Task model
        tag_ids = task_dict.pop('tag_ids', [])
        task_dict.pop('status', None)
        task_dict.pop('estimated_hours', None)
        task_dict.pop('tags', None)  # Remove tags string field
        task_dict.pop('is_recurring', None)  # Remove is_recurring field
        
        # Calculate start date (next workday at 8am)
        start_date = self.get_next_workday_8am(datetime.utcnow())
        
        # If no deadline is set, get project deadline and subtract one day
        if not task_dict.get('deadline') and task_dict.get('project_id'):
            project = db.query(Project).filter(Project.id == task_dict['project_id']).first()
            if project and project.end_date:
                # Set deadline to one day before project end date
                project_end = project.end_date
                task_deadline = (project_end - timedelta(days=1)).replace(hour=16, minute=0, second=0, microsecond=0)
                # Ensure deadline is not on weekend
                while task_deadline.weekday() >= 5:
                    task_deadline -= timedelta(days=1)
                task_dict['deadline'] = task_deadline
        
        # Set all default values
        task_dict.update({
            "created_by": current_user_id,
            "state": TaskState.IN_PROGRESS,  # Default state
            "priority": "normal",    # Default priority
            "description": "",       # Default empty description
            "planned_hours": 0.0,    # Default planned hours
            "progress": 0.0,         # Default progress
            "parent_id": None,       # Default no parent
            "assigned_to": None,     # Default no assignee
            "milestone_id": None,    # Default no milestone
            "company_id": None,      # Default no company
            "start_date": start_date,  # Set start date to next workday at 8am
            "end_date": None,        # Default no end date
        })

        # Create task with all fields
        task = Task(**task_dict)
        db.add(task)
        db.commit()
        db.refresh(task)

        # Add tags if tag_ids were provided
        if tag_ids:
            from models.tag import Tag
            tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
            task.tags = tags  # Set tags directly instead of extending
            db.commit()
            db.refresh(task)

        return task

    def update_task_state(self, db: Session, task: Task, new_state: str, current_user_id: int) -> Task:
        """Update task state and handle completion status"""
        # Check project permissions
        if task.project_id:
            if not self.permission_service.can_modify_project(db, current_user_id, task.project_id):
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to update tasks in this project"
                )

        # Set start date when task moves to IN_PROGRESS for the first time
        if new_state == TaskState.IN_PROGRESS and task.state == TaskState.NULL:
            task.start_date = datetime.utcnow()
            
            # Also check if project should start
            project = task.project
            if project and not project.start_date:
                project.start_date = datetime.utcnow()
                db.add(project)

        task.state = new_state
        
        # Update task based on state
        if new_state == TaskState.DONE:
            task.end_date = datetime.utcnow()
            task.progress = 100.0
        
        db.commit()
        db.refresh(task)

        # After state change, mark task and project for immediate metrics update
        metrics_worker.mark_entity_changed("task", task.id)
        if task.project_id:
            metrics_worker.mark_entity_changed("project", task.project_id)
        
        return task

    def update_task_stage(self, db: Session, task: Task, new_stage_id: int, current_user_id: int) -> Task:
        """Update task stage and handle completion status based on stage type"""
        # Check project permissions
        if task.project_id:
            if not self.permission_service.can_modify_project(db, current_user_id, task.project_id):
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to update tasks in this project"
                )
        
        # Get the new stage
        new_stage = db.query(TaskStage).filter(TaskStage.id == new_stage_id).first()
        if not new_stage:
            raise HTTPException(status_code=404, detail="Stage not found")
        
        # Check if the stage name indicates completion
        completion_stage_names = {'done', 'completed', 'end', 'closed', 'complete', 'finished'}
        is_completion_stage = any(name in new_stage.name.lower() for name in completion_stage_names)
        
        task.stage_id = new_stage_id
        task.date_last_stage_update = func.now()
        
        # Update task status if moving to a completion stage
        if is_completion_stage:
            task.state = TaskState.DONE
            # Set end date
            now = datetime.utcnow()
            if now.weekday() < 5 and time(8, 0) <= now.time() <= time(16, 0):
                task.end_date = now
            else:
                end_date = now
                while end_date.weekday() >= 5:
                    end_date -= timedelta(days=1)
                task.end_date = end_date.replace(hour=16, minute=0, second=0, microsecond=0)
            task.progress = 100.0
        
        db.commit()
        db.refresh(task)

        # After stage change, mark task and project for immediate metrics update
        metrics_worker.mark_entity_changed("task", task.id)
        if task.project_id:
            metrics_worker.mark_entity_changed("project", task.project_id)
        
        return task

    def update_task(self, db: Session, task_id: int, task_data: dict, current_user_id: int) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Update a task.
        
        Args:
            db: Database session
            task_id: ID of the task to update
            task_data: Updated task data
            current_user_id: ID of the user making the update
            
        Returns:
            Tuple containing (updated_task_dict, error_message)
        """
        try:
            # Check if task exists
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return None, f"Task with ID {task_id} not found"

            # Check project permissions
            if task.project_id:
                if not self.permission_service.can_modify_project(db, current_user_id, task.project_id):
                    return None, "You don't have permission to update tasks in this project"
            
            # Check start_date permission if it's being updated
            if "start_date" in task_data:
                if not ScheduledTaskService.can_set_start_date(db, current_user_id, task.project_id):
                    return None, "Only superusers and project managers can set task start dates"
                    
                # Validate start_date is in the future
                if task_data["start_date"] and task_data["start_date"] < datetime.utcnow():
                    return None, "Start date must be in the future"

            # Validate project exists if specified
            if task_data.get("project_id"):
                check_query = text("SELECT id FROM projects WHERE id = :project_id")
                project = db.execute(check_query, {"project_id": task_data["project_id"]}).fetchone()
                if not project:
                    return None, f"Project with ID {task_data['project_id']} not found"
            
            # Validate assignee exists if specified
            if task_data.get("assigned_to"):
                check_query = text("SELECT id FROM users WHERE id = :assigned_to")
                assignee = db.execute(check_query, {"assigned_to": task_data["assigned_to"]}).fetchone()
                if not assignee:
                    return None, f"User with ID {task_data['assigned_to']} not found"
            
            # Validate milestone exists if specified
            if task_data.get("milestone_id"):
                check_query = text("SELECT id FROM milestones WHERE id = :milestone_id")
                milestone = db.execute(check_query, {"milestone_id": task_data["milestone_id"]}).fetchone()
                if not milestone:
                    return None, f"Milestone with ID {task_data['milestone_id']} not found"
            
            # Build update query dynamically
            update_fields = []
            params = {"task_id": task_id}
            
            # Map of field names to their column names
            field_map = {
                "name": "name",
                "description": "description",
                "state": "state",
                "priority": "priority",
                "start_date": "start_date",
                "deadline": "deadline",
                "end_date": "end_date",
                "planned_hours": "planned_hours",
                "project_id": "project_id",
                "stage_id": "stage_id",
                "assigned_to": "assigned_to",
                "milestone_id": "milestone_id",
                "company_id": "company_id",
                "parent_id": "parent_id",
                "is_recurring": "is_recurring",
                "tags": "tags",
                "email_cc": "email_cc",
                "email_from": "email_from",
                "displayed_image_id": "displayed_image_id",
                "progress": "progress"
            }
            
            for field, column in field_map.items():
                if field in task_data and task_data[field] is not None:
                    update_fields.append(f"{column} = :{field}")
                    params[field] = task_data[field]
            
            if not update_fields:
                return get_task_by_id(db, task_id), None
            
            # Add updated_at timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            
            # Build and execute update query
            update_query = text(f"""
                UPDATE tasks 
                SET {', '.join(update_fields)}
                WHERE id = :task_id
                RETURNING id, name, description, state, priority, deadline, 
                          planned_hours, assigned_to, created_by, project_id,
                          created_at, updated_at, progress, stage_id
            """)
            
            result = db.execute(update_query, params).fetchone()
            db.commit()
            
            if not result:
                return None, "Failed to update task"
            
            # Convert result to dictionary with all required fields
            task = {
                "id": result.id,
                "name": result.name,
                "description": result.description,
                "state": result.state,
                "priority": result.priority,
                "deadline": result.deadline,
                "planned_hours": result.planned_hours,
                "assigned_to": result.assigned_to,
                "created_by": result.created_by,
                "project_id": result.project_id,
                "created_at": result.created_at,
                "updated_at": result.updated_at,
                "progress": result.progress if hasattr(result, 'progress') else 0.0,
                "stage_id": result.stage_id
            }
            
            # After successful update, mark task and project for immediate metrics update
            metrics_worker.mark_entity_changed("task", task_id)
            if task.project_id:
                metrics_worker.mark_entity_changed("project", task.project_id)
            
            return task, None
        
        except Exception as e:
            db.rollback()
            return None, f"Error updating task: {str(e)}"

def get_task_by_id(db: Session, task_id: int) -> Dict[str, Any]:
    """
    Get a task by ID.
    
    Args:
        db: Database session
        task_id: ID of the task to retrieve
        
    Returns:
        Task dictionary with all related data including tags
    """
    query = text("""
    SELECT 
        t.id, t.name, t.description, t.state, t.priority, t.deadline,
        t.planned_hours, t.created_by, t.assigned_to, t.project_id,
        t.created_at, t.updated_at,
        array_agg(DISTINCT jsonb_build_object(
            'id', tg.id,
            'name', tg.name,
            'color', tg.color,
            'active', tg.active
        )) FILTER (WHERE tg.id IS NOT NULL) as tags
    FROM tasks t
    LEFT JOIN task_tag tt ON t.id = tt.task_id
    LEFT JOIN tags tg ON tt.tag_id = tg.id
    WHERE t.id = :task_id
    GROUP BY t.id, t.name, t.description, t.state, t.priority, t.deadline,
             t.planned_hours, t.created_by, t.assigned_to, t.project_id,
             t.created_at, t.updated_at
    """)
    
    result = db.execute(query, {"task_id": task_id}).fetchone()
    
    if not result:
        return None
    
    task_dict = {
        "id": result[0],
        "name": result[1],
        "description": result[2],
        "state": result[3],
        "priority": result[4],
        "deadline": result[5],
        "planned_hours": result[6],
        "created_by": result[7],
        "assigned_to": result[8],
        "project_id": result[9],
        "created_at": result[10],
        "updated_at": result[11],
        "tags": result[12] if result[12] else []
    }
    
    return task_dict

def get_tasks(db: Session, skip: int = 0, limit: int = 100, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Get tasks with optional filtering.
    
    Args:
        db: Database session
        skip: Number of tasks to skip
        limit: Maximum number of tasks to return
        filters: Dictionary of filter conditions (e.g., state, assigned_to)
        
    Returns:
        List of task dictionaries
    """
    filters = filters or {}
    
    # Build query dynamically based on filters
    query_parts = [
        """
        SELECT 
            id, name, description, state, priority, deadline,
            planned_hours, assigned_to, created_by, project_id,
            created_at, updated_at, progress, stage_id
        FROM tasks
        WHERE 1=1
        """
    ]
    
    query_params = {}
    
    # Apply filters
    if "state" in filters:
        query_parts.append("AND state = :state")
        query_params["state"] = filters["state"]
        
    if "priority" in filters:
        query_parts.append("AND priority = :priority")
        query_params["priority"] = filters["priority"]
        
    if "project_id" in filters:
        query_parts.append("AND project_id = :project_id")
        query_params["project_id"] = filters["project_id"]
        
    if "assigned_to" in filters:
        query_parts.append("AND assigned_to = :assigned_to")
        query_params["assigned_to"] = filters["assigned_to"]
        
    if "created_by" in filters:
        query_parts.append("AND created_by = :created_by")
        query_params["created_by"] = filters["created_by"]
    
    query_parts.append("ORDER BY created_at DESC LIMIT :limit OFFSET :skip")
    query_params["limit"] = limit
    query_params["skip"] = skip
    
    query = text("\n".join(query_parts))
    results = db.execute(query, query_params).fetchall()
    
    tasks = []
    for row in results:
        tasks.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "state": row[3],
            "priority": row[4],
            "deadline": row[5],
            "planned_hours": row[6],
            "assigned_to": row[7],
            "created_by": row[8],
            "project_id": row[9],
            "created_at": row[10],
            "updated_at": row[11],
            "progress": row[12],
            "stage_id": row[13]
        })
    
    return tasks

def delete_task(db: Session, task_id: int, current_user_id: int) -> Optional[str]:
    """
    Delete a task.
    
    Args:
        db: Database session
        task_id: ID of the task to delete
        
    Returns:
        Error message if any
    """
    try:
        # Check if task exists
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return f"Task with ID {task_id} not found"

        # Check project permissions
        if task.project_id:
            permission_service = PermissionService()
            if not permission_service.can_modify_project(db, current_user_id, task.project_id):
                return "You don't have permission to delete tasks in this project"

        # Delete task
        delete_query = text("DELETE FROM tasks WHERE id = :task_id")
        db.execute(delete_query, {"task_id": task_id})
        db.commit()
        
        return None
    
    except Exception as e:
        db.rollback()
        return f"Error deleting task: {str(e)}" 