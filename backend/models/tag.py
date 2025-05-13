from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

# Association tables
task_tag = Table(
    'task_tag',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

project_tag = Table(
    'project_tag',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

class Tag(Base):
    """Tag model for project and task categorization"""
    __tablename__ = "tags"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    color = Column(Integer, default=1)  # Color index (1-11) as per Odoo
    active = Column(Boolean, default=True)
    
    # Audit fields
    create_uid = Column(Integer, ForeignKey("users.id"), nullable=True)
    create_date = Column(DateTime(timezone=True), server_default=func.now())
    write_uid = Column(Integer, ForeignKey("users.id"), nullable=True)
    write_date = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[create_uid])
    last_editor = relationship("User", foreign_keys=[write_uid])
    projects = relationship("Project", secondary=project_tag, back_populates="tags")
    tasks = relationship("Task", secondary=task_tag, back_populates="tags")

    def __repr__(self):
        return f"<Tag {self.name}>" 