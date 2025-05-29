from sqlalchemy.orm import Session
from models.project import Project, ProjectMember, ProjectRole
from models.user import User
from typing import Optional

class PermissionService:
    @staticmethod
    def can_modify_project(db: Session, user_id: int, project_id: int) -> bool:
        """
        Check if a user can modify a project's resources
        Returns True if:
        1. User is a superuser
        2. User is the project owner
        3. User is a project manager for this project
        """
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Superuser can do anything
        if user.is_superuser:
            return True

        # Get project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return False

        # Project owner can do anything
        if project.owner_id == user_id:
            return True

        # Check if user is project manager
        project_member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        ).first()

        return project_member is not None and project_member.has_manager_permissions()

    @staticmethod
    def get_user_project_role(db: Session, user_id: int, project_id: int) -> Optional[ProjectRole]:
        """Get the user's role in a project"""
        project_member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        ).first()

        return project_member.role if project_member else None 