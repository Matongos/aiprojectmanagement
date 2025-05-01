from sqlalchemy import create_engine, text
from config import settings

def reset_database():
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        # Create a connection
        with engine.connect() as connection:
            # Drop all tables and the alembic_version table
            connection.execute(text("""
                DROP SCHEMA public CASCADE;
                CREATE SCHEMA public;
                GRANT ALL ON SCHEMA public TO postgres;
                GRANT ALL ON SCHEMA public TO public;
            """))
            connection.commit()
            print("Successfully reset database")
            
    except Exception as e:
        print(f"Error resetting database: {e}")

if __name__ == "__main__":
    reset_database() 