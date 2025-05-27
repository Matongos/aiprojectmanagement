from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .base import Base
from datetime import datetime
from sqlalchemy.sql import text

class MetricType(str, enum.Enum):
    PERFORMANCE = "performance"
    QUALITY = "quality"
    RESOURCE = "resource"
    TIMELINE = "timeline"
    COLLABORATION = "collaboration"

class ProjectMetrics(Base):
    """Enhanced project metrics tracking"""
    __tablename__ = "project_metrics"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete='CASCADE'), nullable=False)
    
    # Timeline Metrics
    schedule_variance = Column(Float, nullable=True, comment='Difference between planned and actual timeline')
    milestone_completion_rate = Column(Float, nullable=True, comment='Percentage of milestones completed on time')
    
    # Budget Metrics
    budget_utilization = Column(Float, nullable=True, comment='Percentage of budget utilized')
    cost_variance = Column(Float, nullable=True, comment='Difference between planned and actual cost')
    
    # Quality Metrics
    defect_density = Column(Float, nullable=True, comment='Number of defects per unit of work')
    rework_rate = Column(Float, nullable=True, comment='Percentage of tasks requiring rework')
    
    # Performance Metrics
    velocity = Column(Float, nullable=True, comment='Average number of tasks completed per time period')
    throughput = Column(Float, nullable=True, comment='Number of completed deliverables per time period')
    
    # Resource Metrics
    resource_utilization = Column(Float, nullable=True, comment='Percentage of available resource time utilized')
    team_load = Column(Float, nullable=True, comment='Average workload per team member')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))
    updated_at = Column(DateTime(timezone=True), onupdate=text('now()'))
    
    # Relationships
    project = relationship("Project", back_populates="metrics")

class TaskMetrics(Base):
    """Enhanced task metrics tracking"""
    __tablename__ = "task_metrics"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete='CASCADE'), nullable=False)
    
    # Time Metrics
    actual_duration = Column(Float, nullable=True, comment='Actual time spent on task')
    time_estimate_accuracy = Column(Float, nullable=True, comment='Ratio of estimated to actual time')
    idle_time = Column(Float, nullable=True, comment='Time task spent without activity')
    
    # Quality Metrics
    review_iterations = Column(Integer, nullable=True, comment='Number of review cycles')
    bug_count = Column(Integer, nullable=True, comment='Number of bugs/issues found')
    rework_hours = Column(Float, nullable=True, comment='Hours spent on rework')
    
    # Complexity Metrics
    complexity_score = Column(Float, nullable=True, comment='Calculated task complexity')
    dependency_count = Column(Integer, nullable=True, comment='Number of task dependencies')
    
    # Collaboration Metrics
    handover_count = Column(Integer, nullable=True, comment='Number of times task changed assignees')
    comment_count = Column(Integer, nullable=True, comment='Number of comments/discussions')
    
    # State Transitions
    state_changes = Column(JSON, nullable=True, comment='History of state transitions')
    blocked_time = Column(Float, nullable=True, comment='Time spent in blocked state')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))
    updated_at = Column(DateTime(timezone=True), onupdate=text('now()'))
    
    # Relationships
    task = relationship("Task", back_populates="metrics")

class ResourceMetrics(Base):
    """Resource utilization and performance metrics"""
    __tablename__ = "resource_metrics"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete='CASCADE'), nullable=False)
    
    # Utilization Metrics
    billable_hours = Column(Float, nullable=True, comment='Hours spent on billable work')
    availability_rate = Column(Float, nullable=True, comment='Percentage of time available for work')
    overtime_hours = Column(Float, nullable=True, comment='Hours worked beyond standard time')
    
    # Performance Metrics
    task_completion_rate = Column(Float, nullable=True, comment='Rate of task completion')
    average_task_duration = Column(Float, nullable=True, comment='Average time per task')
    productivity_score = Column(Float, nullable=True, comment='Calculated productivity metric')
    
    # Skill Utilization
    skill_utilization = Column(JSON, nullable=True, comment='Utilization rate per skill')
    learning_curve = Column(Float, nullable=True, comment='Improvement in task completion time')
    
    # Collaboration Metrics
    collaboration_score = Column(Float, nullable=True, comment='Measure of team collaboration')
    response_time = Column(Float, nullable=True, comment='Average time to respond to assignments')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))
    updated_at = Column(DateTime(timezone=True), onupdate=text('now()'))
    
    # Relationships
    user = relationship("User", back_populates="metrics")
    project = relationship("Project", back_populates="resource_metrics") 