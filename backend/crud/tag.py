from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.tag import Tag
from schemas.tag import TagCreate, TagUpdate
from crud.base import CRUDBase

class CRUDTag(CRUDBase[Tag, TagCreate, TagUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Tag]:
        """Get a tag by its name"""
        return db.query(Tag).filter(Tag.name == name).first()

    def get_active(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Tag]:
        """Get all active tags"""
        return (
            db.query(Tag)
            .filter(Tag.active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_owner(
        self, db: Session, *, obj_in: TagCreate, owner_id: int
    ) -> Tag:
        """Create a new tag with owner information"""
        obj_in_data = obj_in.model_dump()
        db_obj = Tag(**obj_in_data, create_uid=owner_id, write_uid=owner_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_with_owner(
        self, db: Session, *, db_obj: Tag, obj_in: TagUpdate, owner_id: int
    ) -> Tag:
        """Update a tag with owner information"""
        update_data = obj_in.model_dump(exclude_unset=True)
        update_data['write_uid'] = owner_id
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def remove(self, db: Session, *, id: int) -> Tag:
        """Archive a tag instead of deleting if it's being used"""
        obj = db.query(Tag).get(id)
        if obj:
            if obj.projects or obj.tasks:
                # Archive instead of delete if tag is in use
                obj.active = False
                db.add(obj)
                db.commit()
                db.refresh(obj)
                return obj
            return super().remove(db, id=id)
        return None

# Create a singleton instance
tag = CRUDTag(Tag) 