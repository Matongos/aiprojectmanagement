from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from crud import notification as notification_crud
from crud import task as task_crud
from schemas.notification import NotificationCreate
from services.email_service import EmailService
from config import settings
from services import user_service
from models.notification import Notification
from models.user import User
from models.project import Project
from models.task import Task

# Set up logging
logger = logging.getLogger(__name__)

class NotificationService:
    """Service for managing notifications."""
    
    def __init__(self):
        self.email_service = EmailService()

    @staticmethod
    def create_notification(db: Session, notification_data: Dict[str, Any]):
        """
        Create a notification with direct dictionary input.
        
        Args:
            db: Database session
            notification_data: Dictionary containing notification data
            
        Returns:
            Created notification object
        """
        notification = NotificationCreate(
            user_id=notification_data["user_id"],
            title=notification_data["title"],
            content=notification_data.get("content"),
            type=notification_data.get("type", "general"),
            reference_type=notification_data.get("reference_type"),
            reference_id=notification_data.get("reference_id"),
            is_read=notification_data.get("is_read", False)
        )
        
        return notification_crud.create_notification(db, notification)
    
    @staticmethod
    def send_notification(
        db: Session,
        user_id: int,
        title: str,
        content: Optional[str] = None,
        notification_type: str = "general",
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        send_email: bool = True
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
            send_email: Whether to also send an email notification
            
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
        
        # Create in-app notification
        db_notification = notification_crud.create_notification(db, notification_data)
        
        # Send email notification if enabled
        if send_email and settings.EMAILS_ENABLED:
            NotificationService._send_email_notification(
                db=db,
                user_id=user_id,
                title=title,
                content=content,
                notification_type=notification_type,
                reference_type=reference_type,
                reference_id=reference_id
            )
        
        return db_notification
    
    @staticmethod
    def send_to_multiple_users(
        db: Session,
        user_ids: List[int],
        title: str,
        content: Optional[str] = None,
        notification_type: str = "general",
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        send_email: bool = True
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
            send_email: Whether to also send email notifications
            
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
        
        # Create in-app notifications
        db_notifications = notification_crud.create_multiple_notifications(db, notifications)
        
        # Send email notifications if enabled
        if send_email and settings.EMAILS_ENABLED:
            for user_id in user_ids:
                NotificationService._send_email_notification(
                    db=db,
                    user_id=user_id,
                    title=title,
                    content=content,
                    notification_type=notification_type,
                    reference_type=reference_type,
                    reference_id=reference_id
                )
                
        return db_notifications
    
    @staticmethod
    def notify_user_mention(
        db: Session,
        mentioned_user_id: int,
        content_preview: str,
        sender_id: int,
        reference_type: str,
        reference_id: int
    ):
        """
        Send a notification to a user who was mentioned.
        
        Args:
            db: Database session
            mentioned_user_id: User ID of the person who was mentioned
            content_preview: Preview of the content where the mention occurred
            sender_id: User ID of the person who mentioned the user
            reference_type: Type of content (e.g., "task", "comment")
            reference_id: ID of the referenced content
            
        Returns:
            Created notification object
        """
        # Get sender info for notification
        sender = user_service.get_user_by_id(db, sender_id)
        if not sender:
            logger.warning(f"Cannot send mention notification: Sender {sender_id} not found")
            return None
            
        sender_name = sender.get("full_name") or sender.get("username")
        
        # Create notification title and content based on reference type
        if reference_type == "task":
            title = f"{sender_name} mentioned you in a task"
        elif reference_type == "comment":
            title = f"{sender_name} mentioned you in a comment"
        else:
            title = f"{sender_name} mentioned you"
            
        content = f"{sender_name} mentioned you: {content_preview}"
        
        return NotificationService.send_notification(
            db=db,
            user_id=mentioned_user_id,
            title=title,
            content=content,
            notification_type="mention",
            reference_type=reference_type,
            reference_id=reference_id
        )
    
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
    
    @staticmethod
    def _send_email_notification(
        db: Session,
        user_id: int,
        title: str,
        content: Optional[str] = None,
        notification_type: str = "general",
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None
    ):
        """
        Send an email notification to a user.
        
        Args:
            db: Database session
            user_id: User ID to send the notification to
            title: Notification title
            content: Notification content
            notification_type: Type of notification
            reference_type: Type of reference (e.g., "task", "project")
            reference_id: ID of the referenced entity
        
        Returns:
            bool: Whether the email was sent successfully
        """
        try:
            # Get user using user_service instead of crud
            user = user_service.get_user_by_id(db, user_id)
            if not user or not user["email"]:
                logger.warning(f"Cannot send email notification: User {user_id} not found or has no email")
                return False
            
            # Check if user has email notifications enabled
            # If the field doesn't exist yet, default to True
            try:
                if "email_notifications_enabled" in user and not user["email_notifications_enabled"]:
                    logger.info(f"Email notifications are disabled for user {user_id}")
                    return False
            except Exception as e:
                logger.warning(f"Error checking email preferences: {str(e)}")
                # Continue anyway as if notifications are enabled
            
            # Base template variables
            template_vars = {
                "user_name": user["full_name"] or user["username"],
                "title": title,
                "content": content or title,
                "unsubscribe_url": f"{settings.BACKEND_CORS_ORIGINS[0]}/unsubscribe?user_id={user_id}" 
                                   if isinstance(settings.BACKEND_CORS_ORIGINS, list) and settings.BACKEND_CORS_ORIGINS 
                                   else "#"
            }
            
            # Determine email template and add template-specific variables
            if reference_type == "task" and reference_id:
                # For task-related notifications
                task = task_crud.get(db, reference_id)
                if task:
                    # Base task URL
                    base_url = settings.BACKEND_CORS_ORIGINS[0] if isinstance(settings.BACKEND_CORS_ORIGINS, list) and settings.BACKEND_CORS_ORIGINS else ""
                    template_vars["action_url"] = f"{base_url}/tasks/{task.id}"
                    
                    # Add task details
                    template_vars["task_details"] = {
                        "title": task.name,
                        "description": task.description,
                        "status": task.status.replace("_", " ").title() if task.status else "Not Set",
                        "priority": task.priority.replace("_", " ").title() if task.priority else "Not Set",
                    }
                    
                    if task.due_date:
                        template_vars["task_details"]["due_date"] = task.due_date.strftime("%Y-%m-%d")
                    
                    if task.project_id:
                        from services import project_service
                        project = project_service.get_project_by_id(db, task.project_id)
                        if project:
                            template_vars["task_details"]["project"] = project["name"]
                            
                    return EmailService.send_template_email(
                        email_to=user["email"],
                        subject=title,
                        template_name="task_notification",
                        template_vars=template_vars
                    )
            
            # For all other notification types, use the general template
            if reference_type and reference_id:
                base_url = settings.BACKEND_CORS_ORIGINS[0] if isinstance(settings.BACKEND_CORS_ORIGINS, list) and settings.BACKEND_CORS_ORIGINS else ""
                template_vars["action_url"] = f"{base_url}/{reference_type}s/{reference_id}"
                template_vars["action_text"] = f"View {reference_type.title()}"
                
            return EmailService.send_template_email(
                email_to=user["email"],
                subject=title,
                template_name="general_notification",
                template_vars=template_vars
            )
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False 

    def notify_project_followers(
        self,
        db: Session,
        project_id: int,
        title: str,
        content: str,
        notification_type: str,
        exclude_user_id: Optional[int] = None
    ) -> List[Notification]:
        """Notify all followers of a project."""
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return []

        notifications = []
        for follower in project.followers:
            if exclude_user_id and follower.id == exclude_user_id:
                continue

            notification = self.create_notification(
                db=db,
                user_id=follower.id,
                title=title,
                content=content,
                notification_type=notification_type,
                reference_type="project",
                reference_id=project_id
            )
            notifications.append(notification)

        return notifications

    def notify_task_followers(
        self,
        db: Session,
        task_id: int,
        title: str,
        content: str,
        notification_type: str,
        exclude_user_id: Optional[int] = None
    ) -> List[Notification]:
        """Notify all followers of a task."""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return []

        notifications = []
        for follower in task.followers:
            if exclude_user_id and follower.id == exclude_user_id:
                continue

            notification = self.create_notification(
                db=db,
                user_id=follower.id,
                title=title,
                content=content,
                notification_type=notification_type,
                reference_type="task",
                reference_id=task_id
            )
            notifications.append(notification)

        return notifications 