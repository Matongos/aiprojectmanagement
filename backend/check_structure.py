from database import engine
from sqlalchemy import inspect

def check_task_stages_structure():
    inspector = inspect(engine)
    columns = inspector.get_columns('task_stages')
    print("task_stages columns:")
    for col in columns:
        print(f"- {col['name']}: {col['type']}")

if __name__ == '__main__':
    check_task_stages_structure() 