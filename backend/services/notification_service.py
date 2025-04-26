from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from crud import notification as notification_crud
from schemas.notification import NotificationCreate


class NotificationService:
    """Service for managing notifications."""
    
    @staticmethod
    def send_notification(
        db: Session,
        user_id: int,
        title: str,
        content: Optional[str] = None,
        notification_type: str = "general",
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None
    ):
        """
        Send a notification to a single user.
        
        Args:
            db: Database session
            user_id: User ID to send the notification to
            title: Notification title
            content: Notification content
            notification_type: Type of notification
            reference_type: Type of reference (e.g., "task", "project")
            reference_id: ID of the referenced entity
            
        Returns:
            Created notification object
        """
        notification_data = NotificationCreate(
            user_id=user_id,
            title=title,
            content=content,
            type=notification_type,
            reference_type=reference_type,
            reference_id=reference_id
        )
        
        return notification_crud.create_notification(db, notification_data)
    
    @staticmethod
    def send_to_multiple_users(
        db: Session,
        user_ids: List[int],
        title: str,
        content: Optional[str] = None,
        notification_type: str = "general",
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None
    ):
        """
        Send the same notification to multiple users.
        
        Args:
            db: Database session
            user_ids: List of user IDs to send notifications to
            title: Notification title
            content: Notification content
            notification_type: Type of notification
            reference_type: Type of reference (e.g., "task", "project")
            reference_id: ID of the referenced entity
            
        Returns:
            List of created notification objects
        """
        notifications = []
        for user_id in user_ids:
            notification_data = NotificationCreate(
                user_id=user_id,
                title=title,
                content=content,
                type=notification_type,
                reference_type=reference_type,
                reference_id=reference_id
            )
            notifications.append(notification_data)
            
        return notification_crud.create_multiple_notifications(db, notifications)
    
    @staticmethod
    def notify_task_assignment(db: Session, task_id: int, task_title: str, user_id: int, assigned_by_id: int):
        """
        Send a notification for a task assignment.
        
        Args:
            db: Database session
            task_id: ID of the assigned task
            task_title: Title of the assigned task
            user_id: User ID of the assignee
            assigned_by_id: User ID of the assigner
            
        Returns:
            Created notification object
        """
        return NotificationService.send_notification(
            db=db,
            user_id=user_id,
            title=f"New Task Assigned: {task_title}",
            content=f"You have been assigned a new task: {task_title}",
            notification_type="task_assignment",
            reference_type="task",
            reference_id=task_id
        )
    
    @staticmethod
    def notify_task_comment(db: Session, task_id: int, task_title: str, comment_by_id: int, user_ids: List[int]):
        """
        Send notifications to users about a new comment on a task.
        
        Args:
            db: Database session
            task_id: ID of the task that was commented on
            task_title: Title of the task
            comment_by_id: User ID of the commenter
            user_ids: List of user IDs to notify (excluding the commenter)
            
        Returns:
            List of created notification objects
        """
        # Remove the commenter from the list of users to notify
        user_ids = [uid for uid in user_ids if uid != comment_by_id]
        
        if not user_ids:
            return []
            
        return NotificationService.send_to_multiple_users(
            db=db,
            user_ids=user_ids,
            title=f"New Comment on Task: {task_title}",
            content=f"A new comment was added to the task: {task_title}",
            notification_type="task_comment",
            reference_type="task",
            reference_id=task_id
        )
    
    @staticmethod
    def notify_task_status_change(db: Session, task_id: int, task_title: str, new_status: str, user_ids: List[int]):
        """
        Send notifications to users about a task status change.
        
        Args:
            db: Database session
            task_id: ID of the task
            task_title: Title of the task
            new_status: New status of the task
            user_ids: List of user IDs to notify
            
        Returns:
            List of created notification objects
        """
        status_display = new_status.replace("_", " ").title()
        
        return NotificationService.send_to_multiple_users(
            db=db,
            user_ids=user_ids,
            title=f"Task Status Changed: {task_title}",
            content=f"The status of task '{task_title}' has been changed to '{status_display}'",
            notification_type="task_status_change",
            reference_type="task",
            reference_id=task_id
        )
    
    @staticmethod
    def notify_due_date_approaching(db: Session, task_id: int, task_title: str, days_remaining: int, user_id: int):
        """
        Send a notification about a task due date approaching.
        
        Args:
            db: Database session
            task_id: ID of the task
            task_title: Title of the task
            days_remaining: Number of days remaining until the due date
            user_id: User ID of the assignee
            
        Returns:
            Created notification object
        """
        return NotificationService.send_notification(
            db=db,
            user_id=user_id,
            title=f"Task Due Soon: {task_title}",
            content=f"The task '{task_title}' is due in {days_remaining} days",
            notification_type="due_date_reminder",
            reference_type="task",
            reference_id=task_id
        ) 