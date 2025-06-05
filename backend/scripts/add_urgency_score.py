import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database import DATABASE_URL

def add_urgency_score():
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # SQL command to add column if it doesn't exist
    sql_command = """
    DO $$ 
    BEGIN 
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                     WHERE table_name='projects' AND column_name='urgency_score') THEN
            ALTER TABLE projects ADD COLUMN urgency_score FLOAT DEFAULT 0.5;
        END IF;
    END $$;
    """
    
    # Execute command
    with engine.connect() as connection:
        connection.execute(text(sql_command))
        connection.commit()

if __name__ == "__main__":
    add_urgency_score()
    print("Urgency score column added successfully!") 