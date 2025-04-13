from database import engine, Base
import models  # This imports all your models
import sys

def main():
    try:
        print("Connecting to existing database...")
        print("Creating tables if they don't exist...")
        
        # Create tables
        Base.metadata.create_all(engine)
        
        print("Connection successful and tables created!")
        
        # Count and list tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Database contains {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
            
        return True
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 