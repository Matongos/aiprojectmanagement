from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List, Tuple

def create_comment(db: Session, comment_data: dict, user_id: int) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Create a new comment.
    
    Args:
        db: Database session
        comment_data: Comment data including content, task_id, parent_id
        user_id: ID of the user creating the comment
        
    Returns:
        Tuple containing (comment_dict, error_message)
    """
    try:
        # Validate task exists
        if "task_id" in comment_data and comment_data["task_id"]:
            check_query = text("SELECT id FROM tasks WHERE id = :task_id")
            task = db.execute(check_query, {"task_id": comment_data["task_id"]}).fetchone()
            if not task:
                return None, f"Task with ID {comment_data['task_id']} not found"
        
        # Validate parent comment exists if provided
        if "parent_id" in comment_data and comment_data["parent_id"]:
            check_query = text("SELECT id FROM comments WHERE id = :parent_id")
            parent = db.execute(check_query, {"parent_id": comment_data["parent_id"]}).fetchone()
            if not parent:
                return None, f"Parent comment with ID {comment_data['parent_id']} not found"
        
        # Insert comment
        insert_query = text("""
        INSERT INTO comments (
            content, task_id, parent_id, created_by, created_at, updated_at
        ) 
        VALUES (
            :content, :task_id, :parent_id, :created_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        RETURNING id, content, task_id, parent_id, created_by, created_at, updated_at
        """)
        
        result = db.execute(
            insert_query, 
            {
                "content": comment_data.get("content", ""),
                "task_id": comment_data.get("task_id"),
                "parent_id": comment_data.get("parent_id"),
                "created_by": user_id
            }
        ).fetchone()
        
        db.commit()
        
        # Get user info
        user_query = text("""
        SELECT id, username, full_name, profile_image_url
        FROM users
        WHERE id = :user_id
        """)
        
        user = db.execute(user_query, {"user_id": user_id}).fetchone()
        
        comment = {
            "id": result[0],
            "content": result[1],
            "task_id": result[2],
            "parent_id": result[3],
            "created_by": result[4],
            "created_at": result[5],
            "updated_at": result[6],
            "user": {
                "id": user[0],
                "username": user[1],
                "full_name": user[2],
                "profile_image_url": user[3]
            },
            "replies": []
        }
        
        return comment, None
    
    except Exception as e:
        db.rollback()
        return None, f"Error creating comment: {str(e)}"

def get_comment_by_id(db: Session, comment_id: int) -> Dict[str, Any]:
    """
    Get a comment by ID with user info.
    
    Args:
        db: Database session
        comment_id: ID of the comment to get
        
    Returns:
        Comment dictionary with user info
    """
    query = text("""
    SELECT 
        c.id, c.content, c.task_id, c.parent_id, c.user_id, 
        c.created_at, c.updated_at,
        u.id as user_id, u.username, u.full_name, u.profile_image_url
    FROM comments c
    JOIN users u ON c.user_id = u.id
    WHERE c.id = :comment_id
    """)
    
    result = db.execute(query, {"comment_id": comment_id}).fetchone()
    
    if not result:
        return None
    
    return {
        "id": result[0],
        "content": result[1],
        "task_id": result[2],
        "parent_id": result[3],
        "user_id": result[4],
        "created_at": result[5],
        "updated_at": result[6],
        "user": {
            "id": result[7],
            "username": result[8],
            "full_name": result[9],
            "profile_image_url": result[10]
        },
        "replies": []  # Will be populated separately if needed
    }

def get_comments(db: Session, skip: int = 0, limit: int = 100, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Get comments with optional filtering.
    
    Args:
        db: Database session
        skip: Number of comments to skip
        limit: Maximum number of comments to return
        filters: Dictionary of filter conditions (e.g., task_id)
        
    Returns:
        List of comment dictionaries
    """
    filters = filters or {}
    
    # Build query dynamically based on filters
    query_parts = [
        """
        SELECT 
            c.id, c.content, c.task_id, c.parent_id, c.user_id, 
            c.created_at, c.updated_at,
            u.id as user_id, u.username, u.full_name, u.profile_image_url
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE 1=1
        """
    ]
    
    query_params = {}
    
    if "task_id" in filters:
        query_parts.append("AND c.task_id = :task_id")
        query_params["task_id"] = filters["task_id"]
    
    query_parts.append("ORDER BY c.created_at DESC LIMIT :limit OFFSET :skip")
    query_params["limit"] = limit
    query_params["skip"] = skip
    
    query = text("\n".join(query_parts))
    results = db.execute(query, query_params).fetchall()
    
    comments = []
    for row in results:
        comments.append({
            "id": row[0],
            "content": row[1],
            "task_id": row[2],
            "parent_id": row[3],
            "user_id": row[4],
            "created_at": row[5],
            "updated_at": row[6],
            "user": {
                "id": row[7],
                "username": row[8],
                "full_name": row[9],
                "profile_image_url": row[10]
            },
            "replies": []  # Will be populated separately if needed
        })
    
    return comments

def update_comment(db: Session, comment_id: int, comment_data: dict) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Update a comment.
    
    Args:
        db: Database session
        comment_id: ID of the comment to update
        comment_data: Updated comment data
        
    Returns:
        Tuple containing (updated_comment_dict, error_message)
    """
    try:
        # Check if comment exists
        check_query = text("SELECT id FROM comments WHERE id = :comment_id")
        existing = db.execute(check_query, {"comment_id": comment_id}).fetchone()
        if not existing:
            return None, f"Comment with ID {comment_id} not found"
        
        # Update comment
        update_query = text("""
        UPDATE comments
        SET content = :content, updated_at = CURRENT_TIMESTAMP
        WHERE id = :comment_id
        RETURNING id, content, task_id, parent_id, user_id, created_at, updated_at
        """)
        
        result = db.execute(
            update_query, 
            {
                "comment_id": comment_id,
                "content": comment_data.get("content", "")
            }
        ).fetchone()
        
        db.commit()
        
        # Get user info
        user_query = text("""
        SELECT id, username, full_name, profile_image_url
        FROM users
        WHERE id = :user_id
        """)
        
        user = db.execute(user_query, {"user_id": result[4]}).fetchone()
        
        comment = {
            "id": result[0],
            "content": result[1],
            "task_id": result[2],
            "parent_id": result[3],
            "user_id": result[4],
            "created_at": result[5],
            "updated_at": result[6],
            "user": {
                "id": user[0],
                "username": user[1],
                "full_name": user[2],
                "profile_image_url": user[3]
            },
            "replies": []
        }
        
        return comment, None
    
    except Exception as e:
        db.rollback()
        return None, f"Error updating comment: {str(e)}"

def delete_comment(db: Session, comment_id: int) -> Optional[str]:
    """
    Delete a comment.
    
    Args:
        db: Database session
        comment_id: ID of the comment to delete
        
    Returns:
        Error message if any
    """
    try:
        delete_query = text("DELETE FROM comments WHERE id = :comment_id")
        db.execute(delete_query, {"comment_id": comment_id})
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        return f"Error deleting comment: {str(e)}"

def get_related_task(db: Session, task_id: int) -> Dict[str, Any]:
    """
    Get task information for a task ID.
    
    Args:
        db: Database session
        task_id: Task ID to get information for
        
    Returns:
        Task dictionary with basic information
    """
    query = text("""
    SELECT id, name, created_by, assigned_to
    FROM tasks
    WHERE id = :task_id
    """)
    
    result = db.execute(query, {"task_id": task_id}).fetchone()
    
    if not result:
        return None
    
    return {
        "id": result[0],
        "name": result[1],
        "created_by": result[2],
        "assigned_to": result[3]
    }