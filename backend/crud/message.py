from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from models.message import Message, MessageType
from schemas.message import MessageCreate, MessageUpdate
from typing import List, Optional

def create_message(db: Session, message: MessageCreate, sender_id: int) -> Message:
    """Create a new message."""
    db_message = Message(
        content=message.content,
        message_type=message.message_type,
        sender_id=sender_id,
        task_id=message.task_id,
        recipient_id=message.recipient_id
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_message(db: Session, message_id: int) -> Optional[Message]:
    """Get a specific message by ID."""
    return db.query(Message).filter(Message.id == message_id).first()

def get_task_messages(db: Session, task_id: int, skip: int = 0, limit: int = 100) -> List[Message]:
    """Get all messages for a specific task."""
    return db.query(Message)\
        .filter(Message.task_id == task_id)\
        .order_by(Message.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_user_messages(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100,
    unread_only: bool = False
) -> List[Message]:
    """Get all messages for a user (both sent and received)."""
    query = db.query(Message).filter(
        or_(
            Message.recipient_id == user_id,
            and_(
                Message.message_type == MessageType.TASK_MESSAGE,
                Message.task_id.isnot(None)
            )
        )
    )
    
    if unread_only:
        query = query.filter(Message.is_read == False)
    
    return query.order_by(Message.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

def update_message(db: Session, message_id: int, message_update: MessageUpdate) -> Optional[Message]:
    """Update a message."""
    db_message = get_message(db, message_id)
    if not db_message:
        return None
    
    update_data = message_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_message, field, value)
    
    db.commit()
    db.refresh(db_message)
    return db_message

def delete_message(db: Session, message_id: int) -> bool:
    """Delete a message."""
    db_message = get_message(db, message_id)
    if not db_message:
        return False
    
    db.delete(db_message)
    db.commit()
    return True

def mark_message_as_read(db: Session, message_id: int) -> Optional[Message]:
    """Mark a message as read."""
    return update_message(db, message_id, MessageUpdate(is_read=True))

def get_unread_messages_count(db: Session, user_id: int) -> int:
    """Get count of unread messages for a user."""
    return db.query(Message)\
        .filter(
            Message.recipient_id == user_id,
            Message.is_read == False
        ).count() 