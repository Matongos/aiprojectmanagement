from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import urllib.parse

# Import all models to ensure they are registered
from models import *

# Load environment variables
load_dotenv()

# Get database connection parameters
user = os.getenv("POSTGRES_USER", "panashe")
password = os.getenv("POSTGRES_PASSWORD", "panashe")
host = os.getenv("POSTGRES_SERVER", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
database = os.getenv("POSTGRES_DB", "aiprojectmanagement")

# Print connection details for debugging
print("Database connection details in database.py:")
print(f"User: {user}")
print(f"Password: {'*' * len(password)}")
print(f"Server: {host}")
print(f"Port: {port}")
print(f"DB: {database}")

# URL encode the password to handle special characters
encoded_password = urllib.parse.quote_plus(password)

# Create the database URL with encoded password
DATABASE_URL = f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}"
print(f"Using DATABASE_URL: {DATABASE_URL}")

# Create base class for models
Base = declarative_base()

# Create engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables on startup
def create_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 