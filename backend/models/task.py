from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, Table, CheckConstraint
from sqlalchemy.orm import relationship, Session, backref
from sqlalchemy.sql import func
from datetime import datetime
from .base import Base
from .task_stage import TaskStage
from schemas.task import TaskState
from .tag import task_tag  # Import the association table

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
        backref="followed_tasks"
    )

    # Many-to-many relationship for task dependencies
    depends_on = relationship(
        "Task",
        secondary=task_dependencies,
        primaryjoin=id==task_dependencies.c.task_id,
        secondaryjoin=id==task_dependencies.c.depends_on_id,
        backref="dependent_tasks"
    )

    def __repr__(self):
        return f"<Task {self.name}>"
    
    def move_to_stage(self, new_stage_id: int, db: Session):
        """Move task to a new stage"""
        old_stage_id = self.stage_id
        self.stage_id = new_stage_id
        self.date_last_stage_update = func.now()
        
        # Update task state based on stage
        new_stage = db.query(TaskStage).filter(TaskStage.id == new_stage_id).first()
        if new_stage:
            if new_stage.fold:  # If stage is folded (typically done/canceled stages)
                self.state = TaskState.DONE
                self.end_date = func.now()
            else:
                # Reset approval states when moving stages
                if self.state in [TaskState.CHANGES_REQUESTED, TaskState.APPROVED]:
                    self.state = TaskState.IN_PROGRESS
        
        return old_stage_id != new_stage_id  # Return True if stage actually changed

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