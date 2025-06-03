from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, JSON
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