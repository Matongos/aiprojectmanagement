from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from crud import notification as crud
from schemas.notification import Notification as NotificationSchema, NotificationCreate, NotificationUpdate
from database import get_db
from routers.auth import get_current_user

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


@router.put("/{notification_id}/read", response_model=NotificationSchema)
async def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Mark a specific notification as read.
    """
    db_notification = crud.get_notification(db, notification_id)
    if db_notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Check if the user is authorized to update this notification
    if db_notification.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to update this notification")
    
    return crud.mark_as_read(db, notification_id)


@router.put("/mark-all-read", response_model=dict)
async def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Mark all notifications for the current user as read.
    """
    updated_count = crud.mark_all_as_read(db, current_user["id"])
    return {"message": f"Marked {updated_count} notifications as read"}


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