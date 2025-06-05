import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect
from database import DATABASE_URL

def check_columns():
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    columns = inspector.get_columns('tasks')
    print('Columns in tasks table:')
    for col in columns:
        print(f"- {col['name']} ({col['type']})")

if __name__ == '__main__':
    check_columns() 