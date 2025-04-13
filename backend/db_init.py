from sqlalchemy import create_engine
import urllib.parse
import os
from dotenv import load_dotenv
from models import Base  # Import your Base from models.py

# Load environment variables
load_dotenv()

def init_db():
    # Get Postgres connection details
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    server = os.getenv("POSTGRES_SERVER", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "aiprojectmanagent")
    
    # URL encode the password to handle special characters
    encoded_password = urllib.parse.quote_plus(password)
    
    # Create the database URL
    db_url = f"postgresql://{user}:{encoded_password}@{server}:{port}/{db}"
    
    # Create the SQLAlchemy engine
    engine = create_engine(db_url)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db() 