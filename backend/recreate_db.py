from database import engine, Base
from models.task import Task
from models.company import Company
from models.task_stage import TaskStage
from models.project import Project
from models.user import User
from models.role import Role, Permission
from models.milestone import Milestone
from models.file_attachment import FileAttachment
from models.activity import Activity
from models.comment import Comment
from models.time_entry import TimeEntry

def recreate_tables():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables recreated successfully!")

if __name__ == "__main__":
    recreate_tables() 