from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from datetime import datetime

from crud import notification as crud
from schemas.notification import Notification as NotificationSchema, NotificationCreate, NotificationUpdate
from database import get_db
from routers.auth import get_current_user
from services.email_service import EmailService
from config import settings

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[NotificationSchema])
async def read_notifications(
    skip: int = 0,
    limit: int = 100,
    unread_only: bool = Query(False, description="Get only unread notifications"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all notifications for the current user.
    
    - **unread_only**: If true, only returns unread notifications.
    """
    return crud.get_user_notifications(
        db, current_user["id"], skip=skip, limit=limit, unread_only=unread_only
    )


@router.get("/unread-count", response_model=int)
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get the count of unread notifications for the current user.
    """
    return crud.get_unread_count(db, current_user["id"])


@router.get("/{notification_id}", response_model=NotificationSchema)
async def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific notification by ID.
    """
    db_notification = crud.get_notification(db, notification_id)
    if db_notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Check if the user is authorized to view this notification
    if db_notification.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this notification")
    
    return db_notification


@router.post("/", response_model=NotificationSchema, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new notification (admin only).
    """
    # Only allow admins/superusers to create notifications for other users
    if not current_user["is_superuser"] and notification.user_id != current_user["id"]:
        raise HTTPException(
            status_code=403, 
            detail="Not authorized to create notifications for other users"
        )
    
    return crud.create_notification(db, notification)


@router.put("/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Mark a specific notification as read."""
    notification = crud.get_notification(db, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if notification.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this notification")
    
    crud.mark_notification_read(db, notification_id)
    return {"message": "Notification marked as read"}


@router.put("/mark-all-read", response_model=dict)
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Mark all notifications as read for the current user."""
    crud.mark_all_notifications_read(db, current_user["id"])
    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a notification.
    """
    db_notification = crud.get_notification(db, notification_id)
    if db_notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Check if the user is authorized to delete this notification
    if db_notification.user_id != current_user["id"] and not current_user["is_superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this notification")
    
    success = crud.delete_notification(db, notification_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete notification")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test-email", response_model=dict)
async def test_email_notification(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Send a test email notification to the current user.
    For testing purposes only, should be disabled in production.
    """
    if not current_user["is_superuser"]:
        raise HTTPException(status_code=403, detail="Only administrators can send test emails")
    
    if not settings.EMAILS_ENABLED:
        return {"message": "Email notifications are disabled in settings"}
    
    user_email = current_user.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="No email address found for your account")
    
    success = EmailService.send_template_email(
        email_to=user_email,
        subject="Test Email Notification",
        template_name="general_notification",
        template_vars={
            "user_name": current_user.get("full_name", current_user.get("username", "User")),
            "title": "Test Email Notification",
            "content": "This is a test email notification from AI Project Management system.",
            "action_url": f"{settings.BACKEND_CORS_ORIGINS[0]}/notifications" if isinstance(settings.BACKEND_CORS_ORIGINS, list) and settings.BACKEND_CORS_ORIGINS else "#",
            "action_text": "View Notifications",
            "details": {
                "Test Item": "This is a test detail",
                "Time Sent": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "System": "AI Project Management"
            },
            "unsubscribe_url": "#"
        }
    )
    
    if success:
        return {"message": "Test email sent successfully", "email": user_email}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test email") 