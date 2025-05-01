from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models.base import Base
from models.user import User
from models.project import Project
from models.task import Task
from models.task_stage import TaskStage
from models.milestone import Milestone
from models.activity import Activity
from models.comment import Comment
from models.notification import Notification
from config import settings

def reset_database():
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        # Create a connection
        with engine.connect() as connection:
            # First drop all indexes
            drop_indexes_sql = """
            DO $$ DECLARE
                r RECORD;
            BEGIN
                -- Drop all indexes except primary key constraints
                FOR r IN (
                    SELECT schemaname, tablename, indexname 
                    FROM pg_indexes 
                    WHERE schemaname = 'public'
                    AND indexname NOT IN (
                        SELECT conname 
                        FROM pg_constraint 
                        WHERE contype = 'p'
                    )
                ) LOOP
                    EXECUTE 'DROP INDEX IF EXISTS ' || quote_ident(r.schemaname) || '.' || quote_ident(r.indexname) || ' CASCADE';
                END LOOP;
            END $$;
            """
            
            # Then drop all other objects
            drop_objects_sql = """
            DO $$ DECLARE
                r RECORD;
            BEGIN
                -- Drop all tables
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
                
                -- Drop all sequences
                FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP
                    EXECUTE 'DROP SEQUENCE IF EXISTS public.' || quote_ident(r.sequence_name) || ' CASCADE';
                END LOOP;
                
                -- Drop all types
                FOR r IN (SELECT typname FROM pg_type WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')) LOOP
                    EXECUTE 'DROP TYPE IF EXISTS public.' || quote_ident(r.typname) || ' CASCADE';
                END LOOP;
            END $$;
            """
            
            # Execute drop statements
            connection.execute(text(drop_indexes_sql))
            connection.execute(text(drop_objects_sql))
            connection.commit()
            print("Successfully dropped all database objects")
            
            # Recreate all tables and indexes
            Base.metadata.create_all(bind=engine)
            print("Successfully recreated all tables and indexes")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    reset_database() 