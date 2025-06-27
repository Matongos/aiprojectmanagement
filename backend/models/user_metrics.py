from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, JSON, Date
from sqlalchemy.sql import func
from .base import Base

class UserProductivityMetrics(Base):
    """Cached user productivity metrics"""
    __tablename__ = "user_productivity_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    productivity_score = Column(Float, default=0.0)
    completed_tasks = Column(Integer, default=0)
    total_time_spent = Column(Float, default=0.0)
    avg_complexity = Column(Float, default=0.0)
    task_breakdown = Column(JSON, nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    analysis_period_days = Column(Integer, default=30)

    def to_dict(self):
        """Convert to dictionary format"""
        return {
            "productivity_score": round(self.productivity_score, 2),
            "metrics": {
                "completed_tasks": self.completed_tasks,
                "total_time_spent": round(self.total_time_spent, 2),
                "avg_task_complexity": round(self.avg_complexity, 2)
            },
            "task_breakdown": self.task_breakdown or [],
            "analysis_period_days": self.analysis_period_days
        }

class UserProductivityHistory(Base):
    """Historical productivity snapshots for trend analysis"""
    __tablename__ = "user_productivity_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)  # Date of the snapshot
    period_type = Column(String(20), nullable=False)  # 'daily', 'weekly', 'monthly'
    
    # Productivity metrics
    productivity_score = Column(Float, default=0.0)
    completed_tasks = Column(Integer, default=0)
    total_time_spent = Column(Float, default=0.0)
    avg_complexity = Column(Float, default=0.0)
    
    # Additional trend metrics
    tasks_started = Column(Integer, default=0)
    tasks_in_progress = Column(Integer, default=0)
    completion_rate = Column(Float, default=0.0)
    avg_completion_time = Column(Float, default=0.0)
    
    # Trend indicators
    score_trend = Column(String(20), default='stable')  # 'up', 'down', 'stable'
    trend_percentage = Column(Float, default=0.0)  # Percentage change from previous period
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        """Convert to dictionary format"""
        return {
            "snapshot_date": self.snapshot_date.isoformat(),
            "period_type": self.period_type,
            "productivity_score": round(self.productivity_score, 2),
            "completed_tasks": self.completed_tasks,
            "total_time_spent": round(self.total_time_spent, 2),
            "avg_complexity": round(self.avg_complexity, 2),
            "tasks_started": self.tasks_started,
            "tasks_in_progress": self.tasks_in_progress,
            "completion_rate": round(self.completion_rate, 2),
            "avg_completion_time": round(self.avg_completion_time, 2),
            "score_trend": self.score_trend,
            "trend_percentage": round(self.trend_percentage, 2)
        } 