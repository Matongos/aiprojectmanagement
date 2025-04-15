import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from services import auth_service

# Load environment variables
load_dotenv()

# Get database connection parameters
user = os.getenv("POSTGRES_USER")
password = "panashe"  # Hardcode the working password
server = os.getenv("POSTGRES_SERVER")
port = os.getenv("POSTGRES_PORT")
db = os.getenv("POSTGRES_DB")

# Create the database URL
DATABASE_URL = f"postgresql://{user}:{password}@{server}:{port}/{db}"
print(f"Using connection string: {DATABASE_URL}")

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Test user credentials
test_username = "testuser2"
test_password = "password123"

# Get a database session
db = SessionLocal()

try:
    # Try to authenticate with our test user
    print(f"Attempting to authenticate {test_username}...")
    user_data, error = auth_service.authenticate_user(db, test_username, test_password)
    
    if error:
        print(f"Authentication failed: {error}")
        
        # Try to directly query the user to see if it exists
        print("Checking if user exists in database...")
        query = text("SELECT id, username, email, hashed_password FROM users WHERE username = :username")
        result = db.execute(query, {"username": test_username}).fetchone()
        
        if result:
            print(f"User found in database: ID={result[0]}, Username={result[1]}, Email={result[2]}")
            
            # Try to verify password directly
            hashed_password = result[3]
            print(f"Stored hashed password: {hashed_password}")
            
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            verification_result = pwd_context.verify(test_password, hashed_password)
            print(f"Password verification result: {verification_result}")
        else:
            print(f"User {test_username} not found in database!")
    else:
        print(f"Authentication successful! User ID: {user_data['user_id']}")
        print(f"Username: {user_data['username']}")
        print(f"Email: {user_data['email']}")
        
except Exception as e:
    print(f"Test error: {e}")
    
finally:
    db.close() 