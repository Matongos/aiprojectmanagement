from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.notification import Notification
from schemas.notification import NotificationCreate, NotificationUpdate
from crud.base import CRUDBase


def get_notification(db: Session, notification_id: int) -> Optional[Notification]:
    """Get a notification by ID."""
    return db.query(Notification).filter(Notification.id == notification_id).first()


def get_user_notifications(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    unread_only: bool = False
) -> List[Notification]:
    """Get all notifications for a user."""
    query = db.query(Notification).filter(Notification.user_id == user_id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
        
    return query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()


def get_unread_count(db: Session, user_id: int) -> int:
    """Get the count of unread notifications for a user."""
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).count()


def create_notification(db: Session, notification: NotificationCreate) -> Notification:
    """Create a new notification."""
    db_notification = Notification(
        title=notification.title,
        content=notification.content,
        type=notification.type,
        reference_type=notification.reference_type,
        reference_id=notification.reference_id,
        user_id=notification.user_id,
        is_read=False
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


def create_multiple_notifications(db: Session, notifications: List[NotificationCreate]) -> List[Notification]:
    """Create multiple notifications at once."""
    db_notifications = []
    for notification in notifications:
        db_notification = Notification(
            title=notification.title,
            content=notification.content,
            type=notification.type,
            reference_type=notification.reference_type,
            reference_id=notification.reference_id,
            user_id=notification.user_id,
            is_read=False
        )
        db.add(db_notification)
        db_notifications.append(db_notification)
    
    db.commit()
    for notification in db_notifications:
        db.refresh(notification)
    
    return db_notifications


def update_notification(db: Session, notification_id: int, notification: NotificationUpdate) -> Optional[Notification]:
    """Update a notification."""
    db_notification = get_notification(db, notification_id)
    if db_notification is None:
        return None
        
    update_data = notification.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_notification, key, value)
        
    db.commit()
    db.refresh(db_notification)
    return db_notification


def mark_as_read(db: Session, notification_id: int) -> Optional[Notification]:
    """Mark a notification as read."""
    return update_notification(db, notification_id, NotificationUpdate(is_read=True))


def mark_all_as_read(db: Session, user_id: int) -> int:
    """Mark all notifications for a user as read."""
    result = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    return result


def delete_notification(db: Session, notification_id: int) -> bool:
    """Delete a notification."""
    db_notification = get_notification(db, notification_id)
    if db_notification is None:
        return False
        
    db.delete(db_notification)
    db.commit()
    return True 