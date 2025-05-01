from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import urllib.parse

# Load environment variables
load_dotenv()

# Get database connection parameters
user = os.getenv("POSTGRES_USER", "panashe")
password = os.getenv("POSTGRES_PASSWORD", "panashe")
host = os.getenv("POSTGRES_SERVER", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
database = os.getenv("POSTGRES_DB", "aiprojectmanagement")

# URL encode the password to handle special characters
encoded_password = urllib.parse.quote_plus(password)

# Create the database URL with encoded password
DATABASE_URL = f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}"

# Create engine
engine = create_engine(DATABASE_URL)

def add_progress_column():
    try:
        # Create a connection
        with engine.connect() as connection:
            # Add the progress column if it doesn't exist
            connection.execute(text("""
                ALTER TABLE projects 
                ADD COLUMN IF NOT EXISTS progress FLOAT DEFAULT 0.0;
            """))
            connection.commit()
            print("✅ Successfully added progress column to projects table")
    except Exception as e:
        print(f"❌ Error adding progress column: {str(e)}")

if __name__ == "__main__":
    add_progress_column() 