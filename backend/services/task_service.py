from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

def create_task(db: Session, task_data: dict, creator_id: int) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Create a new task.
    
    Args:
        db: Database session
        task_data: Task data with title, description, status, etc.
        creator_id: ID of the user creating the task
        
    Returns:
        Tuple containing (task_dict, error_message)
    """
    try:
        # Validate project exists if specified
        if "project_id" in task_data and task_data["project_id"]:
            check_query = text("SELECT id FROM projects WHERE id = :project_id")
            project = db.execute(check_query, {"project_id": task_data["project_id"]}).fetchone()
            if not project:
                return None, f"Project with ID {task_data['project_id']} not found"
        
        # Validate assignee exists if specified
        if "assignee_id" in task_data and task_data["assignee_id"]:
            check_query = text("SELECT id FROM users WHERE id = :assignee_id")
            assignee = db.execute(check_query, {"assignee_id": task_data["assignee_id"]}).fetchone()
            if not assignee:
                return None, f"User with ID {task_data['assignee_id']} not found"
        
        # Set defaults for fields
        now = datetime.utcnow()
        status = task_data.get("status", "to_do")
        priority = task_data.get("priority", "medium")
        
        # Insert task
        insert_query = text("""
        INSERT INTO tasks (
            title, description, status, priority, due_date,
            estimated_hours, tags, created_by, assignee_id, project_id,
            created_at, updated_at
        ) 
        VALUES (
            :title, :description, :status, :priority, :due_date,
            :estimated_hours, :tags, :created_by, :assignee_id, :project_id,
            :created_at, :updated_at
        )
        RETURNING id, title, description, status, priority, due_date,
                 estimated_hours, tags, created_by, assignee_id, project_id,
                 created_at, updated_at
        """)
        
        result = db.execute(
            insert_query, 
            {
                "title": task_data.get("title", ""),
                "description": task_data.get("description"),
                "status": status,
                "priority": priority,
                "due_date": task_data.get("due_date"),
                "estimated_hours": task_data.get("estimated_hours"),
                "tags": task_data.get("tags"),
                "created_by": creator_id,
                "assignee_id": task_data.get("assignee_id"),
                "project_id": task_data.get("project_id"),
                "created_at": now,
                "updated_at": now
            }
        ).fetchone()
        
        db.commit()
        
        task = {
            "id": result[0],
            "title": result[1],
            "description": result[2],
            "status": result[3],
            "priority": result[4],
            "due_date": result[5],
            "estimated_hours": result[6],
            "tags": result[7],
            "created_by": result[8],
            "assignee_id": result[9],
            "project_id": result[10],
            "created_at": result[11],
            "updated_at": result[12]
        }
        
        return task, None
    
    except Exception as e:
        db.rollback()
        return None, f"Error creating task: {str(e)}"

def get_task_by_id(db: Session, task_id: int) -> Dict[str, Any]:
    """
    Get a task by ID.
    
    Args:
        db: Database session
        task_id: ID of the task to retrieve
        
    Returns:
        Task dictionary
    """
    query = text("""
    SELECT 
        id, title, description, status, priority, due_date,
        estimated_hours, tags, created_by, assignee_id, project_id,
        created_at, updated_at
    FROM tasks
    WHERE id = :task_id
    """)
    
    result = db.execute(query, {"task_id": task_id}).fetchone()
    
    if not result:
        return None
    
    return {
        "id": result[0],
        "title": result[1],
        "description": result[2],
        "status": result[3],
        "priority": result[4],
        "due_date": result[5],
        "estimated_hours": result[6],
        "tags": result[7],
        "created_by": result[8],
        "assignee_id": result[9],
        "project_id": result[10],
        "created_at": result[11],
        "updated_at": result[12]
    }

def get_tasks(db: Session, skip: int = 0, limit: int = 100, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Get tasks with optional filtering.
    
    Args:
        db: Database session
        skip: Number of tasks to skip
        limit: Maximum number of tasks to return
        filters: Dictionary of filter conditions (e.g., status, assignee_id)
        
    Returns:
        List of task dictionaries
    """
    filters = filters or {}
    
    # Build query dynamically based on filters
    query_parts = [
        """
        SELECT 
            id, title, description, status, priority, due_date,
            estimated_hours, tags, created_by, assignee_id, project_id,
            created_at, updated_at
        FROM tasks
        WHERE 1=1
        """
    ]
    
    query_params = {}
    
    # Apply filters
    if "status" in filters:
        query_parts.append("AND status = :status")
        query_params["status"] = filters["status"]
        
    if "priority" in filters:
        query_parts.append("AND priority = :priority")
        query_params["priority"] = filters["priority"]
        
    if "project_id" in filters:
        query_parts.append("AND project_id = :project_id")
        query_params["project_id"] = filters["project_id"]
        
    if "assignee_id" in filters:
        query_parts.append("AND assignee_id = :assignee_id")
        query_params["assignee_id"] = filters["assignee_id"]
        
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
            "title": row[1],
            "description": row[2],
            "status": row[3],
            "priority": row[4],
            "due_date": row[5],
            "estimated_hours": row[6],
            "tags": row[7],
            "created_by": row[8],
            "assignee_id": row[9],
            "project_id": row[10],
            "created_at": row[11],
            "updated_at": row[12]
        })
    
    return tasks

def update_task(db: Session, task_id: int, task_data: dict) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Update a task.
    
    Args:
        db: Database session
        task_id: ID of the task to update
        task_data: Updated task data
        
    Returns:
        Tuple containing (updated_task_dict, error_message)
    """
    try:
        # Check if task exists
        check_query = text("SELECT id FROM tasks WHERE id = :task_id")
        existing = db.execute(check_query, {"task_id": task_id}).fetchone()
        if not existing:
            return None, f"Task with ID {task_id} not found"
        
        # Validate project exists if specified
        if "project_id" in task_data and task_data["project_id"]:
            check_query = text("SELECT id FROM projects WHERE id = :project_id")
            project = db.execute(check_query, {"project_id": task_data["project_id"]}).fetchone()
            if not project:
                return None, f"Project with ID {task_data['project_id']} not found"
        
        # Validate assignee exists if specified
        if "assignee_id" in task_data and task_data["assignee_id"]:
            check_query = text("SELECT id FROM users WHERE id = :assignee_id")
            assignee = db.execute(check_query, {"assignee_id": task_data["assignee_id"]}).fetchone()
            if not assignee:
                return None, f"User with ID {task_data['assignee_id']} not found"
        
        # Build update query dynamically
        update_fields = []
        params = {"task_id": task_id}
        
        for field in ["title", "description", "status", "priority", "due_date", 
                      "estimated_hours", "tags", "assignee_id", "project_id"]:
            if field in task_data and task_data[field] is not None:
                update_fields.append(f"{field} = :{field}")
                params[field] = task_data[field]
        
        if not update_fields:
            # No fields to update, just return the current task
            return get_task_by_id(db, task_id), None
        
        # Add updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        # Build and execute update query
        update_query = text(f"""
            UPDATE tasks 
            SET {', '.join(update_fields)}
            WHERE id = :task_id
            RETURNING id, title, description, status, priority, due_date,
                    estimated_hours, tags, created_by, assignee_id, project_id,
                    created_at, updated_at
        """)
        
        result = db.execute(update_query, params).fetchone()
        db.commit()
        
        if not result:
            return None, "Failed to update task"
        
        task = {
            "id": result[0],
            "title": result[1],
            "description": result[2],
            "status": result[3],
            "priority": result[4],
            "due_date": result[5],
            "estimated_hours": result[6],
            "tags": result[7],
            "created_by": result[8],
            "assignee_id": result[9],
            "project_id": result[10],
            "created_at": result[11],
            "updated_at": result[12]
        }
        
        return task, None
    
    except Exception as e:
        db.rollback()
        return None, f"Error updating task: {str(e)}"

def delete_task(db: Session, task_id: int) -> Optional[str]:
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
        check_query = text("SELECT id FROM tasks WHERE id = :task_id")
        existing = db.execute(check_query, {"task_id": task_id}).fetchone()
        if not existing:
            return f"Task with ID {task_id} not found"
        
        # Delete task
        delete_query = text("DELETE FROM tasks WHERE id = :task_id")
        db.execute(delete_query, {"task_id": task_id})
        db.commit()
        
        return None
    
    except Exception as e:
        db.rollback()
        return f"Error deleting task: {str(e)}" 