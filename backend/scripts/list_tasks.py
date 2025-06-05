import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import DATABASE_URL
from models.task import Task

def list_tasks():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    tasks = session.query(Task).limit(5).all()
    print("\nAvailable tasks:")
    print("-" * 80)
    for task in tasks:
        print(f"ID: {task.id}")
        print(f"Name: {task.name}")
        print(f"Priority: {task.priority}")
        print(f"Priority Source: {task.priority_source}")
        print(f"Priority Score: {task.priority_score}")
        print(f"Priority Reasoning: {task.priority_reasoning}")
        print("-" * 80)

if __name__ == "__main__":
    list_tasks() 