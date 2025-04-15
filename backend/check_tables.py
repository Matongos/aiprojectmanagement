import sqlalchemy as sa
from sqlalchemy import inspect
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection parameters
user = os.getenv("POSTGRES_USER", "panashe")
password = os.getenv("POSTGRES_PASSWORD", "panashe")  # Use 'panashe' as default password
host = os.getenv("POSTGRES_SERVER", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
database = os.getenv("POSTGRES_DB", "aiprojectmanagement")

# Create the database URL
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{database}"

# Connect to database
engine = sa.create_engine(DATABASE_URL)

# Get table inspector
inspector = inspect(engine)

# Get table names
tables = inspector.get_table_names()

print("Tables in database:", tables) 