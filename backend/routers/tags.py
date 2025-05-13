from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.tag import TagCreate, TagUpdate, Tag
from crud.tag import tag
from routers.auth import get_current_user

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[Tag])
async def get_tags(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all tags.
    - skip: Number of records to skip
    - limit: Maximum number of records to return
    - active_only: If True, return only active tags
    """
    if active_only:
        return tag.get_active(db, skip=skip, limit=limit)
    return tag.get_multi(db, skip=skip, limit=limit)

@router.post("/", response_model=Tag, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_in: TagCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new tag.
    - name: Tag name (required, unique)
    - color: Color index (1-11)
    - active: Whether the tag is active
    """
    # Check if tag with same name exists
    db_tag = tag.get_by_name(db, name=tag_in.name)
    if db_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists"
        )
    return tag.create_with_owner(db, obj_in=tag_in, owner_id=current_user["id"])

@router.get("/{tag_id}", response_model=Tag)
async def get_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific tag by ID."""
    db_tag = tag.get(db, id=tag_id)
    if not db_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    return db_tag

@router.put("/{tag_id}", response_model=Tag)
async def update_tag(
    tag_id: int,
    tag_in: TagUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a tag.
    - name: New tag name (optional)
    - color: New color index (optional)
    - active: New active status (optional)
    """
    db_tag = tag.get(db, id=tag_id)
    if not db_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # If name is being updated, check for uniqueness
    if tag_in.name and tag_in.name != db_tag.name:
        existing_tag = tag.get_by_name(db, name=tag_in.name)
        if existing_tag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag with this name already exists"
            )
    
    return tag.update_with_owner(
        db,
        db_obj=db_tag,
        obj_in=tag_in,
        owner_id=current_user["id"]
    )

@router.delete("/{tag_id}", response_model=Tag)
async def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete (or archive) a tag.
    If the tag is in use (assigned to projects or tasks), it will be archived instead of deleted.
    """
    db_tag = tag.get(db, id=tag_id)
    if not db_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    result = tag.remove(db, id=tag_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tag"
        )
    return result

@router.get("/search/{name}", response_model=List[Tag])
async def search_tags(
    name: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Search tags by name.
    Returns tags whose names contain the search term (case-insensitive).
    """
    from sqlalchemy import func
    
    return (
        db.query(tag.model)
        .filter(
            func.lower(tag.model.name).contains(name.lower()),
            tag.model.active == True
        )
        .limit(limit)
        .all()
    ) 