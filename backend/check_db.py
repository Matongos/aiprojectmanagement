from sqlalchemy import create_engine, text
import sys

# Database connection URL
DATABASE_URL = "postgresql://panashe:panashe@localhost:5432/aiprojectmanagement"

def check_database():
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Try to connect and get table names
        with engine.connect() as connection:
            # Get all table names
            result = connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
            tables = [row[0] for row in result]
            
            print("Successfully connected to the database!")
            print("\nExisting tables:")
            for table in tables:
                print(f"- {table}")
            
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    check_database() 