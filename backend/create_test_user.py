from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
import urllib.parse
from passlib.context import CryptContext
import sys

# Add the current directory to the path so we can import models
sys.path.append('.')

# Load environment variables
load_dotenv()

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_test_user():
    """Create a test user directly in the database using raw SQL."""
    try:
        # Get database connection parameters
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        server = os.getenv("POSTGRES_SERVER")
        port = os.getenv("POSTGRES_PORT")
        db = os.getenv("POSTGRES_DB")
        
        # Encode password to handle special characters
        quoted_password = urllib.parse.quote_plus(password)
        
        # Create database URL
        db_url = f"postgresql://{user}:{quoted_password}@{server}:{port}/{db}"
        
        # Create engine
        engine = create_engine(db_url)
        
        # Create a session
        with Session(engine) as session:
            # Check if test user already exists
            check_query = text("SELECT id FROM users WHERE username = :username")
            result = session.execute(check_query, {"username": "testuser"}).fetchone()
            
            if result:
                print(f"Test user already exists with ID: {result[0]}")
                return
            
            # Hash the password
            hashed_password = pwd_context.hash("testpassword")
            
            # Insert a new user with raw SQL to avoid relationship issues
            insert_query = text("""
            INSERT INTO users (email, username, full_name, hashed_password, is_active, is_superuser) 
            VALUES (:email, :username, :full_name, :hashed_password, :is_active, :is_superuser)
            RETURNING id
            """)
            
            result = session.execute(
                insert_query, 
                {
                    "email": "test@example.com",
                    "username": "testuser",
                    "full_name": "Test User",
                    "hashed_password": hashed_password,
                    "is_active": True,
                    "is_superuser": False
                }
            ).fetchone()
            
            session.commit()
            
            print(f"Test user created successfully with ID: {result[0]}")
            print(f"Username: testuser")
            print(f"Password: testpassword")
            
    except Exception as e:
        print(f"Error creating test user: {e}")

if __name__ == "__main__":
    create_test_user() 