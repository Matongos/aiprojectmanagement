from sqlalchemy.orm import Session
from models.notification import Notification

def mark_notification_read(db: Session, notification_id: int) -> None:
    """Mark a specific notification as read."""
    db.query(Notification).filter(Notification.id == notification_id).update({"is_read": True})
    db.commit()

def mark_all_notifications_read(db: Session, user_id: int) -> None:
    """Mark all notifications as read for a specific user."""
    db.query(Notification)\
        .filter(Notification.user_id == user_id)\
        .update({"is_read": True})
    db.commit()

def get_unread_count(db: Session, user_id: int) -> int:
    """Get the count of unread notifications for a user."""
    return db.query(Notification)\
        .filter(Notification.user_id == user_id)\
        .filter(Notification.is_read == False)\
        .count() 