from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from schemas.message import MessageCreate, MessageResponse, MessageUpdate
from services import message_service
from routers.auth import get_current_user
from schemas.user import User

router = APIRouter(
    prefix="/messages",
    tags=["messages"],
    responses={401: {"description": "Unauthorized"}}
)

@router.post("/", response_model=MessageResponse)
async def create_message(
    message: MessageCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new message."""
    try:
        # Add sender_id to message data
        message_data = message.dict()
        message_data["sender_id"] = current_user.get("id")
        
        if not message_data["sender_id"]:
            raise HTTPException(status_code=400, detail="Invalid user ID")
        
        # Create message
        result = await message_service.create_message(db, message_data)
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create message")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}", response_model=List[MessageResponse])
async def get_task_messages(
    task_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all messages for a specific task."""
    try:
        messages = message_service.get_task_messages(db, task_id, skip, limit)
        return messages
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch task messages: {str(e)}"
        )

@router.get("/user/me", response_model=List[MessageResponse])
async def get_my_messages(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all messages for the current user."""
    try:
        messages = message_service.get_user_messages(
            db, 
            current_user["id"], 
            skip, 
            limit,
            unread_only
        )
        return messages
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch user messages: {str(e)}"
        )

@router.patch("/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: int,
    message_update: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a message."""
    try:
        # Check if message exists and user has permission
        existing_message = message_service.get_message(db, message_id)
        if not existing_message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        if existing_message.sender_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to update this message")
        
        # Update message
        updated_message = message_service.update_message(db, message_id, message_update)
        if not updated_message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Prepare response
        response = MessageResponse.model_validate(updated_message)
        response.sender = {
            "id": current_user["id"],
            "username": current_user["username"],
            "full_name": current_user["full_name"],
            "profile_image_url": current_user.get("profile_image_url")
        }
        
        if updated_message.recipient:
            response.recipient = {
                "id": updated_message.recipient.id,
                "username": updated_message.recipient.username,
                "full_name": updated_message.recipient.full_name,
                "profile_image_url": updated_message.recipient.profile_image_url
            }
        
        if updated_message.task:
            response.task = {
                "id": updated_message.task.id,
                "name": updated_message.task.name
            }
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update message: {str(e)}"
        )

@router.post("/{message_id}/read", response_model=MessageResponse)
async def mark_as_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Mark a message as read."""
    try:
        result = message_service.mark_message_as_read(db, message_id, current_user["id"])
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Message not found or you don't have permission to mark it as read"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark message as read: {str(e)}"
        )

@router.get("/unread/count")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get count of unread messages for the current user."""
    try:
        count = message_service.get_unread_messages_count(db, current_user["id"])
        return {"count": count}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get unread message count: {str(e)}"
        ) 