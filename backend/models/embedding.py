from sqlalchemy import Column, Integer, String, DateTime, text
from sqlalchemy.sql import func
from .base import Base

class Embedding(Base):
    """Model for storing vector embeddings of various entities"""
    __tablename__ = "embeddings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False, index=True)  # e.g., 'task', 'project', 'time_entry'
    entity_id = Column(Integer, nullable=False, index=True)
    embedding = Column(String, nullable=False)  # JSON string representation of the vector
    embedding_vector = Column('embedding_vector', String)  # Will be handled as vector in PostgreSQL
    model = Column(String, nullable=False, index=True)  # e.g., 'codellama', 'neural-chat'
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Embedding {self.entity_type}:{self.entity_id}>" 