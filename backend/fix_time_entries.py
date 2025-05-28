from sqlalchemy import create_engine, text
from config import settings

def fix_time_entries():
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Drop the table if it exists
        conn.execute(text("DROP TABLE IF EXISTS time_entries CASCADE"))
        conn.commit()
        
        # Create the table with all required columns
        conn.execute(text("""
            CREATE TABLE time_entries (
                id SERIAL PRIMARY KEY,
                duration FLOAT NOT NULL DEFAULT 0.0,
                description TEXT,
                activity_type VARCHAR(50),
                is_billable BOOLEAN DEFAULT true,
                is_running BOOLEAN DEFAULT false,
                task_id INTEGER NOT NULL REFERENCES tasks(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                project_id INTEGER REFERENCES projects(id),
                productivity_score FLOAT,
                efficiency_metrics JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE
            )
        """))
        conn.commit()
        
        print("Time entries table recreated successfully!")

if __name__ == "__main__":
    fix_time_entries() 