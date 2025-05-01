from database import Base, engine
from models.task_stage import TaskStage
from models.task import Task
from models.projects import Project
from models.user import User
from models.role import Role, Permission
from models.activity import Activity
from models.comment import Comment
from models.file_attachment import FileAttachment

def recreate_tables():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables recreated successfully!")

if __name__ == "__main__":
    recreate_tables() 