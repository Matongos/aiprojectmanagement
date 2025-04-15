from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
import urllib.parse
from passlib.context import CryptContext

# Load environment variables
load_dotenv()

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Superuser data
test_user = {
    "username": "matongo",
    "password": "matongo",
    "email": "matongo@example.com",
    "full_name": "matongo matongo"
}

# Get database connection parameters
user = os.getenv("POSTGRES_USER", "panashe")
password = os.getenv("POSTGRES_PASSWORD", "panashe")
server = os.getenv("POSTGRES_SERVER", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
db = os.getenv("POSTGRES_DB", "aiprojectmanagement")

# Create database URL
DATABASE_URL = f"postgresql://{user}:{password}@{server}:{port}/{db}"

print(f"Connecting to database: {DATABASE_URL}")

# Create engine and connect
try:
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # Check if user already exists
            check_query = text("SELECT id FROM users WHERE username = :username OR email = :email")
            existing_user = conn.execute(check_query, {
                "username": test_user["username"], 
                "email": test_user["email"]
            }).fetchone()
            
            if existing_user:
                print(f"User {test_user['username']} or email {test_user['email']} already exists.")
                trans.rollback()
            else:
                # Hash the password
                hashed_password = pwd_context.hash(test_user["password"])
                
                # Insert new user as superuser
                insert_query = text("""
                INSERT INTO users (email, username, full_name, hashed_password, is_active, is_superuser, created_at, updated_at) 
                VALUES (:email, :username, :full_name, :hashed_password, TRUE, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id, email, username, is_superuser
                """)
                
                result = conn.execute(
                    insert_query, 
                    {
                        "email": test_user["email"],
                        "username": test_user["username"],
                        "full_name": test_user["full_name"],
                        "hashed_password": hashed_password
                    }
                ).fetchone()
                
                # Commit the transaction
                trans.commit()
                
                print(f"Superuser created successfully!")
                print(f"ID: {result[0]}")
                print(f"Email: {result[1]}")
                print(f"Username: {result[2]}")
                print(f"Is Superuser: {result[3]}")
                print(f"\nLogin credentials:")
                print(f"Username: {test_user['username']}")
                print(f"Password: {test_user['password']}")
                
        except Exception as e:
            trans.rollback()
            print(f"Error during user creation: {e}")
            raise
            
except Exception as e:
    print(f"Database connection error: {e}") 