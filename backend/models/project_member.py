from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
from .enums import ProjectRole

class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = {'extend_existing': True}

    project_id = Column(Integer, ForeignKey('projects.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role = Column(Enum(ProjectRole, name='projectrole', create_constraint=True, validate_strings=True), default=ProjectRole.MEMBER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships with overlaps parameters
    project = relationship("Project", back_populates="project_members", overlaps="members")
    user = relationship("User", back_populates="project_memberships", overlaps="member_of_projects")

    def __repr__(self):
        return f"<ProjectMember {self.project_id}:{self.user_id}>"

    def has_manager_permissions(self) -> bool:
        """Check if the member has project manager permissions"""
        return self.role == ProjectRole.MANAGER

    class Config:
        orm_mode = True 