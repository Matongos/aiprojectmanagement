from database import engine, Base
import models  # This imports all your models
import sys

def main():
    try:
        # Attempt to create all tables
        print("Creating database tables...")
        Base.metadata.create_all(engine)
        print("Database tables created successfully!")
        
        # Let's count the number of tables created
        from sqlalchemy import inspect
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        print(f"Created {len(table_names)} tables:")
        for table in table_names:
            print(f"  - {table}")
        
        return True
    except Exception as e:
        print(f"Error setting up database: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 