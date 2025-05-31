from sqlalchemy.orm import Session
from models.project import Project, ProjectMember, ProjectRole
from models.user import User
from fastapi import HTTPException
from typing import List, Optional

class ProjectService:
    def can_access_project(self, db: Session, user_id: int, project_id: int) -> bool:
        """Check if a user has access to a project"""
        try:
            # Get the project
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return False

            # Check if user is the project creator
            if project.created_by == user_id:
                return True

            # Check if user is a project member
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            ).first()

            return member is not None

        except Exception as e:
            print(f"Error checking project access: {e}")
            return False

    def can_modify_project(self, db: Session, user_id: int, project_id: int) -> bool:
        """Check if a user has modification rights for a project"""
        try:
            # Get the project
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return False

            # Check if user is the project creator
            if project.created_by == user_id:
                return True

            # Check if user is a project manager
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
                ProjectMember.role == ProjectRole.MANAGER
            ).first()

            return member is not None

        except Exception as e:
            print(f"Error checking project modification rights: {e}")
            return False

    def get_user_projects(self, db: Session, user_id: int) -> List[Project]:
        """Get all projects a user has access to"""
        try:
            # Get projects where user is a member
            member_projects = db.query(Project).join(
                ProjectMember,
                Project.id == ProjectMember.project_id
            ).filter(
                ProjectMember.user_id == user_id
            ).all()

            # Get projects created by user
            created_projects = db.query(Project).filter(
                Project.created_by == user_id
            ).all()

            # Combine and deduplicate projects
            all_projects = list(set(member_projects + created_projects))
            return all_projects

        except Exception as e:
            print(f"Error getting user projects: {e}")
            return []

    def get_project_with_tasks_and_users(self, db: Session, project_id: int):
        """Get project with related tasks and users"""
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project 