import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database import DATABASE_URL

def add_priority_columns():
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # SQL commands to add columns if they don't exist
    sql_commands = [
        """
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                         WHERE table_name='tasks' AND column_name='priority_source') THEN
                ALTER TABLE tasks ADD COLUMN priority_source VARCHAR(50) DEFAULT 'auto';
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                         WHERE table_name='tasks' AND column_name='priority_score') THEN
                ALTER TABLE tasks ADD COLUMN priority_score FLOAT DEFAULT 0.0;
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                         WHERE table_name='tasks' AND column_name='priority_reasoning') THEN
                ALTER TABLE tasks ADD COLUMN priority_reasoning JSONB DEFAULT '[]';
            END IF;
        END $$;
        """
    ]
    
    # Execute each command
    with engine.connect() as connection:
        for command in sql_commands:
            connection.execute(text(command))
            connection.commit()

if __name__ == "__main__":
    add_priority_columns()
    print("Priority columns added successfully!") 