from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base

class Company(Base):
    """Company model for multi-company support"""
    __tablename__ = "companies"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Foreign Keys
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tasks = relationship("Task", back_populates="company")
    creator = relationship("User", back_populates="created_companies", overlaps="created_companies")

    def __repr__(self):
        return f"<Company {self.name}>" 