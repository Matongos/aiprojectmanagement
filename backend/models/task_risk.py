from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base  # Import Base from local base.py
from datetime import datetime

class TaskRisk(Base):
    """Model for storing task risk analysis results"""
    __tablename__ = "task_risks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    time_sensitivity = Column(Float, nullable=False)
    complexity = Column(Float, nullable=False)
    priority = Column(Float, nullable=False)
    risk_factors = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationship
    task = relationship("Task", back_populates="risk_analyses") 