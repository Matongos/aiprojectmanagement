import psycopg2
import os
from dotenv import load_dotenv
import traceback
import sys
import time

# Load environment variables
load_dotenv()

# Get database connection parameters
user = os.getenv("POSTGRES_USER", "panashe")
password = os.getenv("POSTGRES_PASSWORD", "panashe")  # Use 'panashe' as default password
host = os.getenv("POSTGRES_SERVER", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
database = os.getenv("POSTGRES_DB", "aiprojectmanagement")

# Print details for debugging
print("Database connection details:")
print(f"User: {user}")
print(f"Password: {'*' * len(password)}")
print(f"Host: {host}")
print(f"Port: {port}")
print(f"DB: {database}")

try:
    # Try to connect to database directly
    print("\nAttempting direct connection to PostgreSQL...")
    conn = psycopg2.connect(
        user=user,
        password=password,
        host=host,
        port=port,
        database=database
    )
    
    print("Connection established!")
    
    # Create a cursor
    cursor = conn.cursor()
    
    # Test query
    print("Executing test query...")
    cursor.execute("SELECT version();")
    
    # Get result
    version = cursor.fetchone()
    print(f"PostgreSQL Version: {version[0]}")
    
    # List all tables
    print("\nListing all tables in database...")
    cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name;
    """)
    
    tables = cursor.fetchall()
    print("Database tables:")
    for table in tables:
        print(f"- {table[0]}")
    
    # Test specific table - users
    print("\nTesting users table...")
    cursor.execute("SELECT COUNT(*) FROM users;")
    user_count = cursor.fetchone()[0]
    print(f"Number of users in database: {user_count}")
    
    # Close cursor and connection
    cursor.close()
    conn.close()
    print("\nConnection test successful!")
    
except Exception as e:
    print(f"\nERROR: {str(e)}")
    print("\nTraceback:")
    traceback.print_exc(file=sys.stdout)
    print("\nConnection test failed!") 