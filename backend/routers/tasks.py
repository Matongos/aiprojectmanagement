from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from models.task import Task
from models.task_stage import TaskStage
from models.user import User
from schemas.task import TaskCreate, TaskUpdate, Task as TaskSchema, TaskState, TaskPriority
from schemas.file_attachment import FileAttachment as FileAttachmentSchema, FileAttachmentCreate
from crud import task as task_crud
from crud import file_attachment as file_attachment_crud
from crud import activity
from schemas.activity import ActivityCreate
from database import get_db
from routers.auth import get_current_user
from schemas.user import User as UserSchema
from services.file_service import FileService
from services.notification_service import NotificationService
from services.task_service import TaskService
from models.projects import Project

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)

# File attachment endpoints
file_service = FileService()
task_service = TaskService()
notification_service = NotificationService()

@router.post("/", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new task with required fields: name, project_id, and stage_id."""
    try:
        # Convert 0 values to None for foreign keys
        task_data = task.model_dump()
        if task_data.get('assigned_to', 0) == 0:
            task_data['assigned_to'] = None
        if task_data.get('parent_id', 0) == 0:
            task_data['parent_id'] = None

        # Validate that the project exists
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {task.project_id} not found"
            )

        # Validate that the stage exists and belongs to the project
        stage = db.query(TaskStage).filter(
            TaskStage.id == task.stage_id,
            TaskStage.project_id == task.project_id
        ).first()
        
        if not stage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stage with ID {task.stage_id} not found in project {task.project_id}"
            )

        # Create the task with modified data
        created_task, error = task_service.create_task(db, task_data, current_user["id"])
        
        if error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
        
        # Ensure proper serialization
        task_dict = TaskSchema.model_validate(created_task).model_dump()
        if hasattr(created_task, 'assignee') and created_task.assignee:
            task_dict['assignee'] = {
                'id': created_task.assignee.id,
                'username': created_task.assignee.username,
                'email': created_task.assignee.email,
                'full_name': created_task.assignee.full_name,
                'profile_image_url': getattr(created_task.assignee, 'profile_image_url', None)
            }
        return TaskSchema.model_validate(task_dict)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}"
        )

@router.get("/", response_model=List[TaskSchema])
async def read_tasks(
    project_id: Optional[int] = None,
    stage_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get tasks with optional filtering"""
    try:
        if project_id:
            tasks = task_crud.get_project_tasks(db, project_id, skip, limit)
        elif stage_id:
            tasks = task_crud.get_tasks_by_stage(db, stage_id, skip, limit)
        elif search:
            tasks = task_crud.search_tasks(db, search_term=search, skip=skip, limit=limit)
        else:
            tasks = task_crud.get_user_tasks(db, current_user["id"], skip, limit)
            
        if not current_user["is_superuser"]:
            tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            # Create base task dictionary
            task_dict = {
                "id": task.id,
                "name": task.name,
                "description": task.description,
                "priority": task.priority,
                "state": task.state,
                "project_id": task.project_id,
                "stage_id": task.stage_id,
                "assigned_to": task.assigned_to,
                "parent_id": task.parent_id,
                "milestone_id": task.milestone_id,
                "company_id": task.company_id,
                "start_date": task.start_date,
                "end_date": task.end_date,
                "deadline": task.deadline,
                "planned_hours": task.planned_hours,
                "created_by": task.created_by,
                "progress": task.progress if task.progress is not None else 0.0,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "date_last_stage_update": task.date_last_stage_update,
                "assignee": None,
                "milestone": None,
                "company": None,
                "depends_on_ids": [],
                "subtask_ids": []
            }
            
            # Handle assignee
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            
            # Handle milestone
            if hasattr(task, 'milestone') and task.milestone:
                task_dict['milestone'] = {
                    'id': task.milestone.id,
                    'name': task.milestone.name,
                    'description': task.milestone.description,
                    'due_date': task.milestone.due_date.isoformat() if task.milestone.due_date else None,
                    'is_completed': task.milestone.is_completed,
                    'is_active': getattr(task.milestone, 'is_active', True)
                }
            
            # Handle company
            if hasattr(task, 'company') and task.company:
                task_dict['company'] = {
                    'id': task.company.id,
                    'name': task.company.name
                }
            
            # Handle dependencies and subtasks
            if hasattr(task, 'depends_on') and task.depends_on:
                task_dict["depends_on_ids"] = [dep.id for dep in task.depends_on]
            
            if hasattr(task, 'children') and task.children:
                task_dict["subtask_ids"] = [child.id for child in task.children]
            
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tasks: {str(e)}"
        )

@router.get("/my", response_model=List[TaskSchema])
async def read_my_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tasks assigned to or created by the current user"""
    try:
        tasks = task_crud.get_user_tasks(db, current_user["id"], skip, limit)
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user tasks: {str(e)}"
        )

@router.get("/{task_id}", response_model=TaskSchema)
async def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get a specific task by ID."""
    try:
        db_task = task_crud.get(db=db, id=task_id)
        if db_task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if not current_user["is_superuser"] and db_task.assigned_to != current_user["id"] and db_task.created_by != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        # Serialize the task manually to avoid pydantic validation issues with the User object
        task_data = {
            "id": db_task.id,
            "name": db_task.name,
            "description": db_task.description,
            "priority": db_task.priority,
            "state": db_task.state,
            "project_id": db_task.project_id,
            "stage_id": db_task.stage_id,
            "assigned_to": db_task.assigned_to,
            "parent_id": db_task.parent_id,
            "milestone_id": db_task.milestone_id,
            "company_id": db_task.company_id,
            "start_date": db_task.start_date,
            "end_date": db_task.end_date,
            "deadline": db_task.deadline,
            "planned_hours": db_task.planned_hours,
            "created_by": db_task.created_by,
            "progress": db_task.progress,
            "created_at": db_task.created_at,
            "updated_at": db_task.updated_at,
            "date_last_stage_update": db_task.date_last_stage_update,
            "assignee": None,
            "milestone": None,
            "company": None,
            "depends_on_ids": [],
            "subtask_ids": [],
            "attachments": []
        }
        
        # Handle assignee
        if hasattr(db_task, 'assignee') and db_task.assignee:
            task_data["assignee"] = {
                'id': db_task.assignee.id,
                'username': db_task.assignee.username,
                'email': db_task.assignee.email,
                'full_name': db_task.assignee.full_name,
                'profile_image_url': getattr(db_task.assignee, 'profile_image_url', None)
            }
        
        # Handle milestone
        if hasattr(db_task, 'milestone') and db_task.milestone:
            task_data["milestone"] = {
                'id': db_task.milestone.id,
                'name': db_task.milestone.name,
                'description': db_task.milestone.description,
                'due_date': db_task.milestone.due_date.isoformat() if db_task.milestone.due_date else None,
                'is_completed': db_task.milestone.is_completed,
                'is_active': getattr(db_task.milestone, 'is_active', True)
            }
        
        # Handle company
        if hasattr(db_task, 'company') and db_task.company:
            task_data["company"] = {
                'id': db_task.company.id,
                'name': db_task.company.name
            }
        
        # Handle dependencies and subtasks
        if hasattr(db_task, 'depends_on') and db_task.depends_on:
            task_data["depends_on_ids"] = [dep.id for dep in db_task.depends_on]
        
        if hasattr(db_task, 'children') and db_task.children:
            task_data["subtask_ids"] = [child.id for child in db_task.children]
        
        # Handle attachments
        if hasattr(db_task, 'attachments') and db_task.attachments:
            attach_data = []
            for attachment in db_task.attachments:
                attach_data.append({
                    'id': attachment.id,
                    'filename': attachment.filename,
                    'original_filename': attachment.original_filename,
                    'file_size': attachment.file_size,
                    'content_type': attachment.content_type,
                    'description': attachment.description,
                    'task_id': attachment.task_id,
                    'created_at': attachment.created_at.isoformat() if attachment.created_at else None,
                    'created_by': attachment.created_by
                })
            task_data["attachments"] = attach_data
        
        # Now create a TaskSchema from our manually constructed dict
        return TaskSchema.model_validate(task_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching task: {str(e)}"
        )

@router.put("/{task_id}", response_model=TaskSchema)
async def update_task(
    task_id: int,
    task: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Update a specific task."""
    try:
        db_task = task_crud.get(db=db, id=task_id)
        if db_task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if not current_user["is_superuser"] and db_task.created_by != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        # Store original values for comparison
        original_state = db_task.state
        original_assignee = db_task.assigned_to
        original_stage = db_task.stage_id
        original_priority = db_task.priority
        
        # Update task
        updated_task = task_crud.update(db=db, db_obj=db_task, obj_in=task)
        
        # Create activity logs for changes
        update_data = task.model_dump(exclude_unset=True)
        for field, new_value in update_data.items():
            old_value = getattr(db_task, field)
            if new_value != old_value:
                # Create descriptive message based on field type
                if field == "state" and new_value != original_state:
                    description = f"Changed task state from {original_state} to {new_value}"
                elif field == "assigned_to" and new_value != original_assignee:
                    # Get assignee names
                    old_assignee = db.query(User).filter(User.id == original_assignee).first() if original_assignee else None
                    new_assignee = db.query(User).filter(User.id == new_value).first() if new_value else None
                    old_name = old_assignee.full_name if old_assignee else "unassigned"
                    new_name = new_assignee.full_name if new_assignee else "unassigned"
                    description = f"Reassigned task from {old_name} to {new_name}"
                elif field == "stage_id" and new_value != original_stage:
                    # Get stage names
                    old_stage = db.query(TaskStage).filter(TaskStage.id == original_stage).first() if original_stage else None
                    new_stage = db.query(TaskStage).filter(TaskStage.id == new_value).first() if new_value else None
                    old_name = old_stage.name if old_stage else "no stage"
                    new_name = new_stage.name if new_stage else "no stage"
                    description = f"Moved task from {old_name} to {new_name}"
                elif field == "priority" and new_value != original_priority:
                    description = f"Changed priority from {original_priority} to {new_value}"
                else:
                    description = f"Updated task {field}"

                # Create activity log
                activity_data = {
                    "activity_type": "task_update",
                    "description": description,
                    "task_id": task_id,
                    "project_id": updated_task.project_id,
                    "user_id": current_user["id"]
                }
                activity.create_activity(db, ActivityCreate(**activity_data))
        
        # Send notifications if status has changed
        if task.state is not None and task.state != original_state:
            # Notify creator and assignee (if different from current user and creator)
            users_to_notify = set()
            if db_task.created_by and db_task.created_by != current_user["id"]:
                users_to_notify.add(db_task.created_by)
            if db_task.assigned_to and db_task.assigned_to != current_user["id"] and db_task.assigned_to != db_task.created_by:
                users_to_notify.add(db_task.assigned_to)
                
            if users_to_notify:
                # Notify all users in users_to_notify
                for user_id in users_to_notify:
                    notification_data = {
                        "user_id": user_id,
                        "title": "Task Status Changed",
                        "content": f"Task '{updated_task.name}' status changed to {task.state}",
                        "type": "task_status",
                        "reference_type": "task",
                        "reference_id": task_id,
                        "is_read": False
                    }
                    notification_service.create_notification(db, notification_data)
        
        # Create base task dictionary for serialization
        task_dict = {
            "id": updated_task.id,
            "name": updated_task.name,
            "description": updated_task.description,
            "priority": updated_task.priority,
            "state": updated_task.state,
            "project_id": updated_task.project_id,
            "stage_id": updated_task.stage_id,
            "assigned_to": updated_task.assigned_to,
            "parent_id": updated_task.parent_id,
            "milestone_id": updated_task.milestone_id,
            "company_id": updated_task.company_id,
            "start_date": updated_task.start_date,
            "end_date": updated_task.end_date,
            "deadline": updated_task.deadline,
            "planned_hours": updated_task.planned_hours,
            "created_by": updated_task.created_by,
            "progress": updated_task.progress if updated_task.progress is not None else 0.0,
            "created_at": updated_task.created_at,
            "updated_at": updated_task.updated_at,
            "date_last_stage_update": updated_task.date_last_stage_update,
            "assignee": None,
            "milestone": None,
            "company": None,
            "depends_on_ids": [],
            "subtask_ids": []
        }
        
        # Handle assignee
        if hasattr(updated_task, 'assignee') and updated_task.assignee:
            task_dict['assignee'] = {
                'id': updated_task.assignee.id,
                'username': updated_task.assignee.username,
                'email': updated_task.assignee.email,
                'full_name': updated_task.assignee.full_name,
                'profile_image_url': getattr(updated_task.assignee, 'profile_image_url', None)
            }
        
        # Handle milestone
        if hasattr(updated_task, 'milestone') and updated_task.milestone:
            task_dict['milestone'] = {
                'id': updated_task.milestone.id,
                'name': updated_task.milestone.name,
                'description': updated_task.milestone.description,
                'due_date': updated_task.milestone.due_date.isoformat() if updated_task.milestone.due_date else None,
                'is_completed': updated_task.milestone.is_completed,
                'is_active': getattr(updated_task.milestone, 'is_active', True)
            }
        
        # Handle company
        if hasattr(updated_task, 'company') and updated_task.company:
            task_dict['company'] = {
                'id': updated_task.company.id,
                'name': updated_task.company.name
            }
        
        # Handle dependencies and subtasks
        if hasattr(updated_task, 'depends_on') and updated_task.depends_on:
            task_dict["depends_on_ids"] = [dep.id for dep in updated_task.depends_on]
        
        if hasattr(updated_task, 'children') and updated_task.children:
            task_dict["subtask_ids"] = [child.id for child in updated_task.children]
        
        return TaskSchema.model_validate(task_dict)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating task: {str(e)}"
        )

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Delete a specific task."""
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not current_user["is_superuser"] and db_task.created_by != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    task_crud.remove(db=db, id=task_id)
    return None

@router.get("/state/{state}", response_model=List[TaskSchema])
async def read_tasks_by_state(
    state: TaskState,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get tasks by state."""
    try:
        tasks = task_crud.get_tasks_by_state(db=db, state=state, skip=skip, limit=limit)
        if not current_user["is_superuser"]:
            tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tasks by state: {str(e)}"
        )

@router.get("/priority/{priority}", response_model=List[TaskSchema])
async def read_tasks_by_priority(
    priority: TaskPriority,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get tasks filtered by priority."""
    try:
        tasks = task_crud.get_tasks_by_priority(
            db=db, priority=priority, skip=skip, limit=limit
        )
        if not current_user["is_superuser"]:
            tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tasks by priority: {str(e)}"
        )

@router.get("/overdue/", response_model=List[TaskSchema])
async def read_overdue_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get all overdue tasks for the current user."""
    try:
        current_date = datetime.utcnow().date()
        tasks = task_crud.get_overdue_tasks(
            db=db, current_date=current_date, skip=skip, limit=limit
        )
        if not current_user["is_superuser"]:
            tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching overdue tasks: {str(e)}"
        )

@router.get("/upcoming/", response_model=List[TaskSchema])
async def read_upcoming_tasks(
    days: int = Query(7, description="Number of days to look ahead"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get tasks due in the next X days."""
    try:
        current_date = datetime.utcnow().date()
        future_date = current_date + timedelta(days=days)
        
        tasks = (
            db.query(Task)
            .filter(
                Task.due_date.between(current_date, future_date),
                Task.status != "done"
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        if not current_user["is_superuser"]:
            tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching upcoming tasks: {str(e)}"
        )

@router.put("/{task_id}/state", response_model=TaskSchema)
async def update_task_state(
    task_id: int,
    state: TaskState,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Update a task's state."""
    try:
        db_task = task_crud.get(db=db, id=task_id)
        if db_task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if not current_user["is_superuser"] and db_task.created_by != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        updated_task = task_crud.update_state(db=db, db_obj=db_task, state=state)
        
        # Ensure proper serialization
        task_dict = TaskSchema.model_validate(updated_task).model_dump()
        if hasattr(updated_task, 'assignee') and updated_task.assignee:
            task_dict['assignee'] = {
                'id': updated_task.assignee.id,
                'username': updated_task.assignee.username,
                'email': updated_task.assignee.email,
                'full_name': updated_task.assignee.full_name,
                'profile_image_url': getattr(updated_task.assignee, 'profile_image_url', None)
            }
        return TaskSchema.model_validate(task_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating task state: {str(e)}"
        )

@router.get("/created/", response_model=List[TaskSchema])
async def read_created_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get all tasks created by the current user."""
    try:
        tasks = (
            db.query(Task)
            .filter(Task.created_by == current_user["id"])
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching created tasks: {str(e)}"
        )

@router.get("/recent", response_model=List[TaskSchema])
async def read_recent_tasks(
    *,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
    limit: int = 5,
):
    """
    Retrieve recent tasks for the current user.
    """
    try:
        tasks = task_crud.get_recent_tasks(
            db=db, user_id=current_user["id"], limit=limit
        )
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching recent tasks: {str(e)}"
        )

@router.get("/over-budget", response_model=List[TaskSchema])
async def read_over_budget_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get tasks where actual hours exceed estimated hours.
    Useful for project management and resource allocation.
    """
    try:
        tasks = task_crud.get_tasks_over_budget(
            db=db, skip=skip, limit=limit
        )
        
        # Filter tasks for regular users to only see their own or assigned tasks
        if not current_user["is_superuser"]:
            tasks = [t for t in tasks if t.assigned_to == current_user["id"] or t.created_by == current_user["id"]]
        
        # Convert tasks to ensure proper serialization
        result = []
        for task in tasks:
            task_dict = TaskSchema.model_validate(task).model_dump()
            # Ensure assignee is a dict if it exists
            if hasattr(task, 'assignee') and task.assignee:
                task_dict['assignee'] = {
                    'id': task.assignee.id,
                    'username': task.assignee.username,
                    'email': task.assignee.email,
                    'full_name': task.assignee.full_name,
                    'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                }
            result.append(TaskSchema.model_validate(task_dict))
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching over-budget tasks: {str(e)}"
        )

@router.post("/{task_id}/attachments", response_model=FileAttachmentSchema, status_code=status.HTTP_201_CREATED)
async def upload_task_attachment(
    task_id: int,
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Upload a file attachment to a task."""
    # Verify task exists and user has permission
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Save the file to disk
    unique_filename, file_path, file_size = await file_service.save_file(file, task_id)
    
    # Create file attachment record in database
    file_data = FileAttachmentCreate(
        filename=unique_filename,
        original_filename=file.filename,
        file_size=file_size,
        content_type=file.content_type or "application/octet-stream",
        description=description,
        task_id=task_id
    )
    
    db_file = file_attachment_crud.create_file_attachment(
        db=db, 
        file_data=file_data, 
        user_id=current_user["id"],
        file_path=file_path
    )
    
    return db_file

@router.get("/{task_id}/attachments", response_model=List[FileAttachmentSchema])
async def get_task_attachments(
    task_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get all file attachments for a task."""
    # Verify task exists
    db_task = task_crud.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return file_attachment_crud.get_task_attachments(db=db, task_id=task_id, skip=skip, limit=limit)

@router.put("/{task_id}/move-stage")
async def move_task_stage(
    task_id: int,
    new_stage_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Move a task to a different stage"""
    try:
        # Get the task
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Get the new stage
        new_stage = db.query(TaskStage).filter(TaskStage.id == new_stage_id).first()
        if not new_stage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stage not found"
            )
        
        # Check if the new stage belongs to the same project
        if new_stage.project_id != task.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot move task to a stage from a different project"
            )
        
        # Move the task to the new stage
        stage_changed = task.move_to_stage(new_stage_id, db)
        
        if stage_changed:
            db.commit()
            db.refresh(task)
            
            # Ensure proper serialization for the response
            task_dict = {
                "message": "Task stage updated successfully",
                "task": None
            }
            
            if task:
                task_data = TaskSchema.model_validate(task).model_dump()
                # Ensure assignee is a dict if it exists
                if hasattr(task, 'assignee') and task.assignee:
                    task_data['assignee'] = {
                        'id': task.assignee.id,
                        'username': task.assignee.username,
                        'email': task.assignee.email,
                        'full_name': task.assignee.full_name,
                        'profile_image_url': getattr(task.assignee, 'profile_image_url', None)
                    }
                task_dict["task"] = task_data
            
            return task_dict
        
        return {"message": "Task is already in this stage"} 
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error moving task to new stage: {str(e)}"
        ) 