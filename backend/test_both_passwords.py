import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection parameters from .env
user = os.getenv("POSTGRES_USER", "panashe")
password = os.getenv("POSTGRES_PASSWORD", "panashe")
host = os.getenv("POSTGRES_SERVER", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
database = os.getenv("POSTGRES_DB", "aiprojectmanagement")

print("Testing database connection...")
try:
    conn = psycopg2.connect(
        dbname=database,
        user=user,
        password=password,
        host=host,
        port=port
    )
    print('Connected successfully!')
    
    # Execute a simple query
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"PostgreSQL version: {version[0]}")
    
    # Close cursor and connection
    cursor.close()
    conn.close()
except Exception as e:
    print(f'Connection failed: {e}') 