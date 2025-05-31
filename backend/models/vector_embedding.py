from sqlalchemy import Column, Integer, String, Float, ARRAY, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class VectorEmbedding(Base):
    __tablename__ = "vector_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)  # e.g., 'task', 'project'
    entity_id = Column(Integer, nullable=False)
    embedding = Column(ARRAY(Float), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True 