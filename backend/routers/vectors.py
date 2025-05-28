from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from services.vector_service import VectorService
from routers.auth import get_current_user

router = APIRouter(prefix="/vectors", tags=["vectors"])

class EmbeddingCreate(BaseModel):
    text: str
    entity_type: str
    entity_id: int
    model: Optional[str] = "neural-chat"

class SimilaritySearch(BaseModel):
    text: str
    entity_type: str
    model: Optional[str] = "neural-chat"
    limit: Optional[int] = 5

class SimilarityResult(BaseModel):
    entity_id: int
    similarity: float

@router.post("/embed")
async def create_embedding(
    data: EmbeddingCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create an embedding for text"""
    vector_service = VectorService(db)
    embedding = await vector_service.create_embedding(
        text=data.text,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        model=data.model
    )
    
    if not embedding:
        raise HTTPException(
            status_code=500,
            detail="Failed to create embedding"
        )
    
    return {"success": True, "embedding_id": embedding.id}

@router.post("/similar", response_model=List[SimilarityResult])
async def find_similar(
    data: SimilaritySearch,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Find similar entities based on text"""
    vector_service = VectorService(db)
    results = await vector_service.find_similar(
        text=data.text,
        entity_type=data.entity_type,
        model=data.model,
        limit=data.limit
    )
    
    return [
        SimilarityResult(entity_id=entity_id, similarity=similarity)
        for entity_id, similarity in results
    ]

@router.delete("/{entity_type}/{entity_id}")
async def delete_embeddings(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete embeddings for an entity"""
    vector_service = VectorService(db)
    success = vector_service.delete_embeddings(entity_type, entity_id)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete embeddings"
        )
    
    return {"success": True} 