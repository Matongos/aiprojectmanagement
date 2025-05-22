from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict
from datetime import datetime
from models.message import Message, MessageType
from models.activity import Activity, ActivityType
from models.notification import Notification, NotificationType
from services.email_service import send_email_notification
from config import settings

async def create_message(db: Session, message_data: dict) -> Optional[Dict]:
    """Create a new message and handle notifications."""
    try:
        # Validate required fields
        if not message_data.get("content"):
            raise ValueError("Message content is required")
        if not message_data.get("message_type"):
            raise ValueError("Message type is required")
        if not message_data.get("sender_id"):
            raise ValueError("Sender ID is required")
        
        # For task messages, validate task_id
        if message_data["message_type"] == "task_message" and not message_data.get("task_id"):
            raise ValueError("Task ID is required for task messages")
            
        # Insert message
        insert_query = text("""
        INSERT INTO messages (
            content, message_type, task_id, sender_id, recipient_id,
            is_read, created_at, updated_at
        ) 
        VALUES (
            :content, :message_type, :task_id, :sender_id, :recipient_id,
            :is_read, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        RETURNING id, content, message_type, task_id, sender_id, recipient_id, is_read, created_at, updated_at
        """)
        
        result = db.execute(
            insert_query, 
            {
                "content": message_data["content"],
                "message_type": message_data["message_type"],
                "task_id": message_data.get("task_id"),
                "sender_id": message_data["sender_id"],
                "recipient_id": message_data.get("recipient_id"),
                "is_read": message_data.get("is_read", False)
            }
        ).fetchone()
        
        if not result:
            raise ValueError("Failed to insert message into database")

        # Create activity log entry
        if result[3]:  # If task_id exists
            activity = Activity(
                activity_type=ActivityType.MESSAGE,
                task_id=result[3],
                user_id=result[4],  # sender_id
                description=f"New message: {result[1][:100]}{'...' if len(result[1]) > 100 else ''}"
            )
            db.add(activity)

        # Get task followers for notifications
        if result[3]:  # If task_id exists
            followers_query = text("""
            SELECT u.id, u.email, u.username, u.email_notifications_enabled
            FROM users u
            JOIN task_followers tf ON u.id = tf.user_id
            WHERE tf.task_id = :task_id AND u.id != :sender_id
            """)
            
            followers = db.execute(followers_query, {
                "task_id": result[3],
                "sender_id": result[4]
            }).fetchall()

            # Create notifications and send emails
            for follower in followers:
                # Create in-app notification
                notification = Notification(
                    user_id=follower[0],
                    notification_type=NotificationType.MESSAGE,
                    content=f"New message in task: {result[1][:100]}{'...' if len(result[1]) > 100 else ''}",
                    reference_id=result[0],  # message_id
                    reference_type="message"
                )
                db.add(notification)

                # Send email if enabled for user
                if follower[3]:  # if email_notifications_enabled
                    await send_email_notification(
                        recipient_email=follower[1],
                        subject="New Task Message",
                        content=f"Hello {follower[2]},\n\nA new message has been posted in a task you're following:\n\n{result[1]}\n\nBest regards,\nYour Project Management System"
                    )

        db.commit()
        
        # Get sender details
        sender = None
        if result[4]:  # sender_id
            sender_query = text("""
            SELECT id, username, full_name, profile_image_url
            FROM users WHERE id = :user_id
            """)
            sender_result = db.execute(sender_query, {"user_id": result[4]}).fetchone()
            if sender_result:
                sender = {
                    "id": sender_result[0],
                    "username": sender_result[1],
                    "full_name": sender_result[2],
                    "profile_image_url": sender_result[3]
                }
        
        # Get recipient details
        recipient = None
        if result[5]:  # recipient_id
            recipient_query = text("""
            SELECT id, username, full_name, profile_image_url
            FROM users WHERE id = :user_id
            """)
            recipient_result = db.execute(recipient_query, {"user_id": result[5]}).fetchone()
            if recipient_result:
                recipient = {
                    "id": recipient_result[0],
                    "username": recipient_result[1],
                    "full_name": recipient_result[2],
                    "profile_image_url": recipient_result[3]
                }
        
        # Get task details
        task = None
        if result[3]:  # task_id
            task_query = text("""
            SELECT id, name FROM tasks WHERE id = :task_id
            """)
            task_result = db.execute(task_query, {"task_id": result[3]}).fetchone()
            if task_result:
                task = {
                    "id": task_result[0],
                    "name": task_result[1]
                }
        
        return {
            "id": result[0],
            "content": result[1],
            "message_type": result[2],
            "task_id": result[3],
            "sender": sender,
            "recipient": recipient,
            "task": task,
            "is_read": result[6],
            "created_at": result[7],
            "updated_at": result[8]
        }
    
    except Exception as e:
        db.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error creating message: {str(e)}\n{error_details}")
        raise Exception(f"Failed to create message: {str(e)}")

def get_task_messages(db: Session, task_id: int, skip: int = 0, limit: int = 100) -> List[Dict]:
    """Get all messages for a specific task."""
    try:
        query = text("""
        SELECT 
            m.id, m.content, m.message_type, m.task_id, 
            m.sender_id, m.recipient_id, m.is_read,
            m.created_at, m.updated_at,
            s.id as sender_id, s.username as sender_username, 
            s.full_name as sender_full_name, s.profile_image_url as sender_profile_image_url,
            r.id as recipient_id, r.username as recipient_username,
            r.full_name as recipient_full_name, r.profile_image_url as recipient_profile_image_url,
            t.id as task_id, t.name as task_name
        FROM messages m
        LEFT JOIN users s ON m.sender_id = s.id
        LEFT JOIN users r ON m.recipient_id = r.id
        LEFT JOIN tasks t ON m.task_id = t.id
        WHERE m.task_id = :task_id
        ORDER BY m.created_at DESC
        OFFSET :skip
        LIMIT :limit
        """)
        
        results = db.execute(query, {
            "task_id": task_id,
            "skip": skip,
            "limit": limit
        }).fetchall()
        
        messages = []
        for result in results:
            message = {
                "id": result[0],
                "content": result[1],
                "message_type": result[2],
                "task_id": result[3],
                "is_read": result[6],
                "created_at": result[7],
                "updated_at": result[8],
                "sender": None,
                "recipient": None,
                "task": None
            }
            
            if result[9]:  # If sender exists
                message["sender"] = {
                    "id": result[9],
                    "username": result[10],
                    "full_name": result[11],
                    "profile_image_url": result[12]
                }
            
            if result[13]:  # If recipient exists
                message["recipient"] = {
                    "id": result[13],
                    "username": result[14],
                    "full_name": result[15],
                    "profile_image_url": result[16]
                }
            
            if result[17]:  # If task exists
                message["task"] = {
                    "id": result[17],
                    "name": result[18]
                }
            
            messages.append(message)
        
        return messages
    
    except Exception as e:
        return []

def get_user_messages(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100,
    unread_only: bool = False
) -> List[Dict]:
    """Get all messages for a user (both sent and received)."""
    try:
        query = text("""
        SELECT 
            m.id, m.content, m.message_type, m.task_id, 
            m.sender_id, m.recipient_id, m.is_read,
            m.created_at, m.updated_at,
            s.id as sender_id, s.username as sender_username, 
            s.full_name as sender_full_name, s.profile_image_url as sender_profile_image_url,
            r.id as recipient_id, r.username as recipient_username,
            r.full_name as recipient_full_name, r.profile_image_url as recipient_profile_image_url,
            t.id as task_id, t.name as task_name
        FROM messages m
        LEFT JOIN users s ON m.sender_id = s.id
        LEFT JOIN users r ON m.recipient_id = r.id
        LEFT JOIN tasks t ON m.task_id = t.id
        WHERE (m.recipient_id = :user_id OR m.sender_id = :user_id)
        """ + (" AND m.is_read = false" if unread_only else "") + """
        ORDER BY m.created_at DESC
        OFFSET :skip
        LIMIT :limit
        """)
        
        results = db.execute(query, {
            "user_id": user_id,
            "skip": skip,
            "limit": limit
        }).fetchall()
        
        messages = []
        for result in results:
            message = {
                "id": result[0],
                "content": result[1],
                "message_type": result[2],
                "task_id": result[3],
                "is_read": result[6],
                "created_at": result[7],
                "updated_at": result[8],
                "sender": None,
                "recipient": None,
                "task": None
            }
            
            if result[9]:  # If sender exists
                message["sender"] = {
                    "id": result[9],
                    "username": result[10],
                    "full_name": result[11],
                    "profile_image_url": result[12]
                }
            
            if result[13]:  # If recipient exists
                message["recipient"] = {
                    "id": result[13],
                    "username": result[14],
                    "full_name": result[15],
                    "profile_image_url": result[16]
                }
            
            if result[17]:  # If task exists
                message["task"] = {
                    "id": result[17],
                    "name": result[18]
                }
            
            messages.append(message)
        
        return messages
    
    except Exception as e:
        return []

def mark_message_as_read(db: Session, message_id: int, user_id: int) -> Optional[Dict]:
    """Mark a message as read."""
    try:
        # Update message
        update_query = text("""
        UPDATE messages 
        SET is_read = true, updated_at = CURRENT_TIMESTAMP
        WHERE id = :message_id AND recipient_id = :user_id
        RETURNING id, content, message_type, task_id, sender_id, recipient_id, is_read, created_at, updated_at
        """)
        
        result = db.execute(
            update_query, 
            {
                "message_id": message_id,
                "user_id": user_id
            }
        ).fetchone()
        
        if not result:
            return None
        
        db.commit()
        
        # Get sender details
        sender = None
        if result[4]:  # sender_id
            sender_query = text("""
            SELECT id, username, full_name, profile_image_url
            FROM users WHERE id = :user_id
            """)
            sender_result = db.execute(sender_query, {"user_id": result[4]}).fetchone()
            if sender_result:
                sender = {
                    "id": sender_result[0],
                    "username": sender_result[1],
                    "full_name": sender_result[2],
                    "profile_image_url": sender_result[3]
                }
        
        # Get recipient details
        recipient = None
        if result[5]:  # recipient_id
            recipient_query = text("""
            SELECT id, username, full_name, profile_image_url
            FROM users WHERE id = :user_id
            """)
            recipient_result = db.execute(recipient_query, {"user_id": result[5]}).fetchone()
            if recipient_result:
                recipient = {
                    "id": recipient_result[0],
                    "username": recipient_result[1],
                    "full_name": recipient_result[2],
                    "profile_image_url": recipient_result[3]
                }
        
        # Get task details
        task = None
        if result[3]:  # task_id
            task_query = text("""
            SELECT id, name FROM tasks WHERE id = :task_id
            """)
            task_result = db.execute(task_query, {"task_id": result[3]}).fetchone()
            if task_result:
                task = {
                    "id": task_result[0],
                    "name": task_result[1]
                }
        
        return {
            "id": result[0],
            "content": result[1],
            "message_type": result[2],
            "task_id": result[3],
            "sender": sender,
            "recipient": recipient,
            "task": task,
            "is_read": result[6],
            "created_at": result[7],
            "updated_at": result[8]
        }
    
    except Exception as e:
        db.rollback()
        return None

def get_unread_messages_count(db: Session, user_id: int) -> int:
    """Get count of unread messages for a user."""
    try:
        query = text("""
        SELECT COUNT(*) 
        FROM messages 
        WHERE recipient_id = :user_id AND is_read = false
        """)
        
        result = db.execute(query, {"user_id": user_id}).scalar()
        return result or 0
    
    except Exception as e:
        return 0 