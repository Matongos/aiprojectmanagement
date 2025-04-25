from sqlalchemy.orm import Session
from typing import List, Optional

from models.file_attachment import FileAttachment
from schemas.file_attachment import FileAttachmentCreate, FileAttachmentUpdate


def get_file_attachments(db: Session, skip: int = 0, limit: int = 100) -> List[FileAttachment]:
    return db.query(FileAttachment).offset(skip).limit(limit).all()


def get_file_attachment(db: Session, file_id: int) -> Optional[FileAttachment]:
    return db.query(FileAttachment).filter(FileAttachment.id == file_id).first()


def get_task_attachments(db: Session, task_id: int, skip: int = 0, limit: int = 100) -> List[FileAttachment]:
    return db.query(FileAttachment).filter(FileAttachment.task_id == task_id).offset(skip).limit(limit).all()


def create_file_attachment(db: Session, file_data: FileAttachmentCreate, user_id: int, file_path: str) -> FileAttachment:
    db_file = FileAttachment(
        filename=file_data.filename,
        original_filename=file_data.original_filename,
        file_path=file_path,
        file_size=file_data.file_size,
        content_type=file_data.content_type,
        description=file_data.description,
        task_id=file_data.task_id,
        uploaded_by=user_id
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file


def update_file_attachment(db: Session, file_id: int, file_data: FileAttachmentUpdate) -> Optional[FileAttachment]:
    db_file = get_file_attachment(db, file_id)
    if db_file is None:
        return None
        
    for key, value in file_data.dict(exclude_unset=True).items():
        setattr(db_file, key, value)
        
    db.commit()
    db.refresh(db_file)
    return db_file


def delete_file_attachment(db: Session, file_id: int) -> bool:
    db_file = get_file_attachment(db, file_id)
    if db_file is None:
        return False
        
    db.delete(db_file)
    db.commit()
    return True 