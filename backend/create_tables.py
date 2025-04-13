from sqlalchemy import create_engine
import urllib.parse
import os
from dotenv import load_dotenv
import models  # This imports all your models
from database import Base  # Import the Base declarative base

# Load environment variables
load_dotenv()

def main():
    # Get PostgreSQL connection parameters
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    server = os.getenv("POSTGRES_SERVER", "localhost") 
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "aiprojectmanagent")
    
    # Encode password to handle special characters
    encoded_password = urllib.parse.quote_plus(password)
    
    # Direct string concatenation to avoid any interpolation issues
    db_url = "postgresql://" + user + ":" + encoded_password + "@" + server + ":" + port + "/" + db
    
    print(f"Connecting to database: {db} as user: {user}")
    
    # Create engine
    engine = create_engine(db_url)
    
    # Create all tables defined in models
    Base.metadata.create_all(engine)
    
    print("Database tables created successfully!")

if __name__ == "__main__":
    main() 