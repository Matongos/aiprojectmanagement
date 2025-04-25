from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Response
from fastapi.responses import FileResponse
from typing import List, Optional
from sqlalchemy.orm import Session
import os

from models.file_attachment import FileAttachment
from schemas.file_attachment import FileAttachment as FileAttachmentSchema
from schemas.file_attachment import FileAttachmentCreate, FileAttachmentUpdate
from crud import file_attachment as crud
from services.file_service import FileService
from database import get_db
from dependencies.auth import get_current_active_user
from models.user import User

router = APIRouter(
    prefix="/file-attachments",
    tags=["file_attachments"],
    responses={404: {"description": "Not found"}},
)

file_service = FileService()

@router.post("/", response_model=FileAttachmentSchema, status_code=status.HTTP_201_CREATED)
async def create_file_attachment(
    task_id: int = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a file attachment for a task
    """
    # Save the file to disk
    unique_filename, file_path, file_size = await file_service.save_file(file, task_id)
    
    # Create file attachment record in the database
    file_data = FileAttachmentCreate(
        filename=unique_filename,
        original_filename=file.filename,
        file_size=file_size,
        content_type=file.content_type or "application/octet-stream",
        description=description,
        task_id=task_id
    )
    
    return crud.create_file_attachment(db, file_data, current_user.id, file_path)

@router.get("/", response_model=List[FileAttachmentSchema])
def read_file_attachments(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve all file attachments
    """
    return crud.get_file_attachments(db, skip=skip, limit=limit)

@router.get("/task/{task_id}", response_model=List[FileAttachmentSchema])
def read_task_attachments(
    task_id: int,
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve all file attachments for a specific task
    """
    return crud.get_task_attachments(db, task_id, skip=skip, limit=limit)

@router.get("/{file_id}", response_model=FileAttachmentSchema)
def read_file_attachment(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve a specific file attachment
    """
    db_file = crud.get_file_attachment(db, file_id)
    if db_file is None:
        raise HTTPException(status_code=404, detail="File attachment not found")
    return db_file

@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Download a file attachment
    """
    db_file = crud.get_file_attachment(db, file_id)
    if db_file is None:
        raise HTTPException(status_code=404, detail="File attachment not found")
    
    file_path = db_file.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        path=file_path,
        filename=db_file.original_filename,
        media_type=db_file.content_type
    )

@router.put("/{file_id}", response_model=FileAttachmentSchema)
def update_file_attachment(
    file_id: int,
    file_data: FileAttachmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a file attachment
    """
    db_file = crud.get_file_attachment(db, file_id)
    if db_file is None:
        raise HTTPException(status_code=404, detail="File attachment not found")
    
    # Check if user is authorized to update this file (owner or admin)
    if db_file.uploaded_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to update this file")
    
    updated_file = crud.update_file_attachment(db, file_id, file_data)
    return updated_file

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file_attachment(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a file attachment
    """
    db_file = crud.get_file_attachment(db, file_id)
    if db_file is None:
        raise HTTPException(status_code=404, detail="File attachment not found")
    
    # Check if user is authorized to delete this file (owner or admin)
    if db_file.uploaded_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to delete this file")
    
    # Delete from filesystem
    file_path = db_file.file_path
    file_service.delete_file(file_path)
    
    # Delete from database
    crud.delete_file_attachment(db, file_id)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT) 