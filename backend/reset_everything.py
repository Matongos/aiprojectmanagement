import os
import shutil
from sqlalchemy import text
from database import engine, Base

def reset_everything():
    print("Starting complete reset...")
    
    # 1. Drop all tables
    print("Dropping all tables...")
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            print("Database schema reset successfully")
    except Exception as e:
        print(f"Error resetting database: {e}")
        return

    # 2. Remove migrations directory
    print("Removing migrations directory...")
    try:
        if os.path.exists("migrations"):
            shutil.rmtree("migrations")
        print("Migrations directory removed")
    except Exception as e:
        print(f"Error removing migrations directory: {e}")
        return

    # 3. Create tables
    print("Creating tables...")
    try:
        Base.metadata.create_all(engine)
        print("Tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")
        return

    print("Reset completed successfully!")

if __name__ == "__main__":
    reset_everything() 