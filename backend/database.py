from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import urllib.parse

# Load environment variables from .env file
load_dotenv()

# Get database connection parameters
user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
server = os.getenv("POSTGRES_SERVER")
port = os.getenv("POSTGRES_PORT")
db = os.getenv("POSTGRES_DB")

# Properly encode the password to handle special characters
quoted_password = urllib.parse.quote_plus(password)

# Create the database URL with proper encoding
DATABASE_URL = f"postgresql://{user}:{quoted_password}@{server}:{port}/{db}"

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 