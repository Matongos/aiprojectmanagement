from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection parameters
user = os.getenv("POSTGRES_USER", "panashe")
password = os.getenv("POSTGRES_PASSWORD", "panashe")
host = os.getenv("POSTGRES_SERVER", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
database = os.getenv("POSTGRES_DB", "aiprojectmanagement")

# Create database URL
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{database}"

# Create engine
engine = create_engine(DATABASE_URL)

# Create MetaData instance
metadata = MetaData()

# Reflect existing tables
metadata.reflect(bind=engine)

# Define task_risks table if it doesn't exist
if 'task_risks' not in metadata.tables:
    task_risks = Table(
        'task_risks',
        metadata,
        Column('id', Integer, primary_key=True),
        Column('task_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False),
        Column('risk_score', Float, nullable=False),
        Column('risk_level', String, nullable=False),
        Column('time_sensitivity', Float, nullable=False),
        Column('complexity', Float, nullable=False),
        Column('priority', Float, nullable=False),
        Column('risk_factors', JSONB),
        Column('recommendations', JSONB),
        Column('metrics', JSONB),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False)
    )

def create_table():
    try:
        # Create the table
        metadata.create_all(engine, tables=[metadata.tables['task_risks']])
        print("Successfully created task_risks table")
        
        # Create indexes
        with engine.connect() as conn:
            conn.execute("""
                CREATE INDEX IF NOT EXISTS ix_task_risks_task_id ON task_risks(task_id);
                CREATE INDEX IF NOT EXISTS ix_task_risks_created_at ON task_risks(created_at);
            """)
            conn.commit()
            print("Successfully created indexes")
            
    except Exception as e:
        print(f"Error creating table: {str(e)}")

if __name__ == "__main__":
    create_table() 