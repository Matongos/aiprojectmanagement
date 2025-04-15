from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from passlib.context import CryptContext

# Load environment variables
load_dotenv()

# Get database connection parameters
user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
server = os.getenv("POSTGRES_SERVER")
port = os.getenv("POSTGRES_PORT")
db = os.getenv("POSTGRES_DB")

# Print out environment variables
print(f"Database connection details:")
print(f"User: {user}")
print(f"Password: {password}")
print(f"Server: {server}")
print(f"Port: {port}")
print(f"DB: {db}")

# Create the database URL
DATABASE_URL = f"postgresql://{user}:{password}@{server}:{port}/{db}"
print(f"Database URL: {DATABASE_URL}")

# Test password hashing
try:
    print("\nTesting password hashing...")
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_context.hash("testpassword")
    print(f"Hashed password: {hashed}")
    verified = pwd_context.verify("testpassword", hashed)
    print(f"Password verification: {verified}")
except Exception as e:
    print(f"Password hashing error: {e}")

# Test database connection
try:
    print("\nTesting database connection...")
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("Database connection successful!")
        
        # Try to query users table
        try:
            user_result = connection.execute(text("SELECT COUNT(*) FROM users"))
            user_count = user_result.scalar()
            print(f"Users in database: {user_count}")
        except Exception as e:
            print(f"Error querying users table: {e}")
            
except Exception as e:
    print(f"Database connection error: {e}") 