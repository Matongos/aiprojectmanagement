from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from passlib.context import CryptContext

# Load environment variables
load_dotenv()

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Get database connection parameters
user = os.getenv("POSTGRES_USER", "panashe")
password = os.getenv("POSTGRES_PASSWORD", "panashe")
host = os.getenv("POSTGRES_SERVER", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
database = os.getenv("POSTGRES_DB", "aiprojectmanagement")

# Create database URL
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{database}"

print(f"Connecting to database: {DATABASE_URL}")

# Create engine and connect
try:
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # Delete existing user if they exist
            delete_query = text("DELETE FROM users WHERE username = :username OR email = :email")
            conn.execute(delete_query, {
                "username": "matongo",
                "email": "matongo@example.com"
            })
            
            # Hash the password
            hashed_password = pwd_context.hash("matongo")
            
            # Insert superuser
            insert_query = text("""
            INSERT INTO users (
                username,
                email,
                full_name,
                hashed_password,
                is_active,
                is_superuser,
                created_at,
                updated_at
            ) VALUES (
                :username,
                :email,
                :full_name,
                :hashed_password,
                TRUE,
                TRUE,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            RETURNING id, username, email, is_superuser
            """)
            
            result = conn.execute(
                insert_query,
                {
                    "username": "matongo",
                    "email": "matongo@example.com",
                    "full_name": "matongo matongo",
                    "hashed_password": hashed_password
                }
            ).fetchone()
            
            # Commit the transaction
            trans.commit()
            
            print("Superuser created successfully!")
            print(f"ID: {result[0]}")
            print(f"Username: {result[1]}")
            print(f"Email: {result[2]}")
            print(f"Is Superuser: {result[3]}")
            print("\nLogin credentials:")
            print("Username: matongo")
            print("Password: matongo")
            
        except Exception as e:
            trans.rollback()
            print(f"Error during user creation: {e}")
            raise
            
except Exception as e:
    print(f"Database connection error: {e}") 