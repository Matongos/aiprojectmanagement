from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, Table, CheckConstraint
from sqlalchemy.orm import relationship, Session, backref
from sqlalchemy.sql import func
from datetime import datetime
from .base import Base
from .task_stage import TaskStage
from schemas.task import TaskState
from .tag import task_tag  # Import the association table
from .metrics import TaskMetrics

# Association table for task dependencies
task_dependencies = Table(
    'task_dependencies',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id'), primary_key=True),
    Column('depends_on_id', Integer, ForeignKey('tasks.id'), primary_key=True),
    extend_existing=True
)

# Association table for task followers
task_followers = Table(
    'task_followers',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    extend_existing=True
)

class Task(Base):
    """Task model for project management"""
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "state IN ('in_progress', 'changes_requested', 'approved', 'canceled', 'done')",
            name='valid_task_states'
        ),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Task name (not title)
    description = Column(Text, nullable=True)
    priority = Column(String(50), default='normal')
    state = Column(String(50), default=TaskState.IN_PROGRESS)
    
    # Foreign Keys
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    stage_id = Column(Integer, ForeignKey("task_stages.id"), nullable=True)
    parent_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)  # Not assignee_id
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)  # Optional company association
    
    # Dates
    start_date = Column(DateTime(timezone=True), nullable=True)  # Not date_start
    end_date = Column(DateTime(timezone=True), nullable=True)  # Not date_end
    deadline = Column(DateTime(timezone=True), nullable=True)  # Not date_deadline
    
    # Time tracking
    planned_hours = Column(Float, default=0.0)  # Not estimated_hours
    progress = Column(Float, nullable=False, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    date_last_stage_update = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    stage = relationship("TaskStage", back_populates="tasks")
    parent = relationship("Task", remote_side=[id], back_populates="subtasks")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_tasks")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_tasks")
    milestone = relationship("Milestone", back_populates="tasks")
    company = relationship("Company", back_populates="tasks")  # Optional company relationship
    attachments = relationship("FileAttachment", back_populates="task", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="task", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    time_entries = relationship("TimeEntry", back_populates="task", cascade="all, delete-orphan")
    subtasks = relationship("Task", back_populates="parent", remote_side=[parent_id])
    tags = relationship("Tag", secondary=task_tag, back_populates="tasks")
    log_notes = relationship("LogNote", back_populates="task", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="task", cascade="all, delete-orphan")
    
    # Followers relationship
    followers = relationship(
        "User",
        secondary=task_followers,
        back_populates="followed_tasks"
    )

    # Many-to-many relationship for task dependencies
    depends_on = relationship(
        "Task",
        secondary=task_dependencies,
        primaryjoin=id==task_dependencies.c.task_id,
        secondaryjoin=id==task_dependencies.c.depends_on_id,
        backref="dependent_tasks"
    )

    # Add metrics relationship
    metrics = relationship("TaskMetrics", back_populates="task", uselist=False, cascade="all, delete-orphan")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize metrics for new tasks
        self.metrics = TaskMetrics(
            task_id=self.id,
            state_changes=[],
            actual_duration=0,
            time_estimate_accuracy=0,
            dependency_count=0,
            comment_count=0,
            idle_time=0,
            review_iterations=0,
            bug_count=0,
            rework_hours=0,
            complexity_score=0,
            handover_count=0,
            blocked_time=0
        )

    def __repr__(self):
        return f"<Task {self.name}>"
    
    def update_metrics(self):
        """Update task metrics."""
        # Initialize metrics if they don't exist
        if not hasattr(self, 'metrics') or not self.metrics:
            self.metrics = TaskMetrics(
                task_id=self.id,
                state_changes=[],
                actual_duration=0,
                time_estimate_accuracy=0,
                dependency_count=0,
                comment_count=0,
                idle_time=0,
                review_iterations=0,
                bug_count=0,
                rework_hours=0,
                complexity_score=0,
                handover_count=0,
                blocked_time=0
            )

        # Update state changes
        if self.state not in self.metrics.state_changes:
            self.metrics.state_changes.append(self.state)
            
        # Calculate actual duration
        total_time = sum(entry.hours for entry in self.time_entries)
        self.metrics.actual_duration = total_time
        
        # Calculate time estimate accuracy
        if self.planned_hours > 0:
            self.metrics.time_estimate_accuracy = total_time / self.planned_hours
        
        # Update complexity metrics
        self.metrics.dependency_count = len(self.depends_on) + len(self.dependent_tasks)
        
        # Update collaboration metrics
        self.metrics.comment_count = len(self.comments)
        
        # Calculate idle time (time without activity)
        activities = sorted(self.activities, key=lambda x: x.created_at)
        if activities:
            idle_time = 0
            for i in range(1, len(activities)):
                time_diff = activities[i].created_at - activities[i-1].created_at
                if time_diff.total_seconds() > 24 * 3600:  # More than 24 hours
                    idle_time += time_diff.total_seconds() / 3600  # Convert to hours
            self.metrics.idle_time = idle_time

    def move_to_stage(self, new_stage_id: int, db: Session) -> bool:
        """Move task to a new stage"""
        if self.stage_id == new_stage_id:
            return False
            
        # Get the new stage
        new_stage = db.query(TaskStage).get(new_stage_id)
        if not new_stage:
            return False
            
        # Update stage and last update time
        self.stage_id = new_stage_id
        self.date_last_stage_update = func.now()
        
        # If stage has auto progress percentage, update task progress
        if new_stage.auto_progress_percentage is not None:
            self.progress = new_stage.auto_progress_percentage
            
        try:
            # Try to update metrics, but don't fail if it's not possible
            self.update_metrics()
        except Exception as e:
            print(f"Warning: Failed to update metrics: {e}")
            # Continue with the stage change even if metrics update fails
            pass
        
        return True

    def get_available_stages(self, db: Session):
        """Get all available stages in the task's project"""
        if self.project_id:
            return (
                db.query(TaskStage)
                .filter(TaskStage.project_id == self.project_id)
                .order_by(TaskStage.sequence)
                .all()
            )
        return []

    def get_previous_stage(self, db: Session):
        """Get the previous stage in sequence"""
        current_stage = db.query(TaskStage).get(self.stage_id)
        if current_stage:
            return (
                db.query(TaskStage)
                .filter(
                    TaskStage.project_id == self.project_id,
                    TaskStage.sequence < current_stage.sequence
                )
                .order_by(TaskStage.sequence.desc())
                .first()
            )
        return None

    def add_follower(self, user_id: int, db: Session) -> bool:
        """Add a follower to the task"""
        from models.user import User
        user = db.query(User).get(user_id)
        if user and user not in self.followers:
            self.followers.append(user)
            return True
        return False

    def remove_follower(self, user_id: int, db: Session) -> bool:
        """Remove a follower from the task"""
        from models.user import User
        user = db.query(User).get(user_id)
        if user and user in self.followers:
            self.followers.remove(user)
            return True
        return False 