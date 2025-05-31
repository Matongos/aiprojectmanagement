import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database import DATABASE_URL

def update_task_states():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Drop existing constraint
        conn.execute(text("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS valid_task_states"))
        
        # Add new constraint
        conn.execute(text("""
            ALTER TABLE tasks ADD CONSTRAINT valid_task_states 
            CHECK (state IN ('null', 'in_progress', 'changes_requested', 'approved', 'canceled', 'done'))
        """))
        
        # Update existing NULL states
        conn.execute(text("UPDATE tasks SET state = 'null' WHERE state IS NULL"))
        
        conn.commit()

if __name__ == "__main__":
    update_task_states()
    print("Task states updated successfully!") 