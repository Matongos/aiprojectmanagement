import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_database():
    """Create the PostgreSQL database if it doesn't exist."""
    # Connection parameters
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    server = os.getenv("POSTGRES_SERVER", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "aiprojectmanagent")
    
    try:
        # Connect to PostgreSQL server (to postgres database by default)
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=server,
            port=port,
            database="postgres"  # Connect to default postgres database
        )
        conn.autocommit = True  # Enable autocommit to create database
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{database}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Creating database: {database}")
            cursor.execute(f"CREATE DATABASE {database}")
            print(f"Database '{database}' created successfully!")
        else:
            print(f"Database '{database}' already exists.")
        
        # Close connection
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")
        return False
    
    return True

if __name__ == "__main__":
    create_database() 