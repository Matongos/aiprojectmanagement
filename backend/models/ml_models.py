from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Table, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class TaskPrediction(Base):
    """Stores ML predictions for tasks"""
    __tablename__ = "task_predictions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    predicted_completion_time = Column(Float)  # in hours
    predicted_success_probability = Column(Float)  # 0 to 1
    confidence_score = Column(Float)  # 0 to 1
    features_used = Column(JSON)  # Store features used for prediction
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    task = relationship("Task", back_populates="predictions")

class TeamPerformanceMetrics(Base):
    """Stores team performance metrics for ML analysis"""
    __tablename__ = "team_performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    time_period = Column(String)  # e.g., "2024-03" for monthly metrics
    velocity = Column(Float)  # tasks completed per time unit
    quality_score = Column(Float)  # based on rework and bugs
    collaboration_score = Column(Float)  # based on interactions and dependencies
    efficiency_score = Column(Float)  # based on time estimates vs actuals
    metrics_data = Column(JSON)  # Additional detailed metrics
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="performance_metrics")

class SuccessPattern(Base):
    """Stores identified success patterns from completed tasks"""
    __tablename__ = "success_patterns"

    id = Column(Integer, primary_key=True, index=True)
    pattern_type = Column(String)  # e.g., "team_composition", "task_planning", "execution"
    pattern_data = Column(JSON)  # The actual pattern details
    confidence_score = Column(Float)  # How confident we are in this pattern
    occurrence_count = Column(Integer)  # How many times this pattern was observed
    impact_score = Column(Float)  # Measured impact on task/project success
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class MLModel(Base):
    """Stores ML model metadata and performance metrics"""
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    model_type = Column(String)  # e.g., "completion_time_predictor", "success_predictor"
    model_version = Column(String)
    performance_metrics = Column(JSON)  # Store model performance metrics
    hyperparameters = Column(JSON)  # Store model hyperparameters
    feature_importance = Column(JSON)  # Store feature importance scores
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_trained = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)

class HistoricalPattern(Base):
    """Stores historical patterns identified in project data"""
    __tablename__ = "historical_patterns"

    id = Column(Integer, primary_key=True, index=True)
    pattern_name = Column(String, nullable=False)
    pattern_description = Column(String)
    pattern_type = Column(String)  # e.g., "risk", "success", "failure"
    detection_method = Column(String)  # e.g., "clustering", "association_rules"
    pattern_data = Column(JSON)  # The actual pattern details
    support = Column(Float)  # Statistical support for the pattern
    confidence = Column(Float)  # Statistical confidence in the pattern
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 