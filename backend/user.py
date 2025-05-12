from sqlalchemy.orm import relationship

# Relationships using string references to avoid circular imports
roles = relationship("Role", secondary="user_role", back_populates="users", lazy="joined")
assigned_tasks = relationship("Task", foreign_keys="Task.assigned_to", back_populates="assignee")
created_tasks = relationship("Task", foreign_keys="Task.created_by", back_populates="creator")
created_projects = relationship("Project", foreign_keys="Project.created_by", back_populates="creator") 