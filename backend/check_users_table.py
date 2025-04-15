import psycopg2
import os
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Get database connection parameters
user = os.getenv("POSTGRES_USER", "panashe")
password = os.getenv("POSTGRES_PASSWORD", "panashe")  # Use 'panashe' as default password
host = os.getenv("POSTGRES_SERVER", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
database = os.getenv("POSTGRES_DB", "aiprojectmanagement")

print("Connecting to database...")
try:
    # Connect to database
    conn = psycopg2.connect(
        user=user,
        password=password,
        host=host,
        port=port,
        database=database
    )
    
    # Create cursor
    cursor = conn.cursor()
    
    # Check if users table exists
    print("Checking if users table exists...")
    cursor.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'users'
    );
    """)
    
    table_exists = cursor.fetchone()[0]
    if not table_exists:
        print("Users table does not exist!")
        sys.exit(1)
    
    print("Users table exists")
    
    # Get table structure
    print("\nUsers table structure:")
    cursor.execute("""
    SELECT column_name, data_type, character_maximum_length, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'users'
    ORDER BY ordinal_position;
    """)
    
    columns = cursor.fetchall()
    for column in columns:
        print(f"- {column[0]}: {column[1]}", end="")
        if column[2]:
            print(f" (max length: {column[2]})", end="")
        print(f" {'NULL' if column[3] == 'YES' else 'NOT NULL'}")
    
    # Check table constraints
    print("\nUsers table constraints:")
    cursor.execute("""
    SELECT tc.constraint_name, tc.constraint_type, kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    WHERE tc.table_name = 'users'
    ORDER BY tc.constraint_type;
    """)
    
    constraints = cursor.fetchall()
    for constraint in constraints:
        print(f"- {constraint[0]}: {constraint[1]} on {constraint[2]}")
    
    # Get some sample data
    print("\nSample users data:")
    cursor.execute("""
    SELECT id, username, email, full_name, is_active, is_superuser, created_at
    FROM users
    LIMIT 3;
    """)
    
    users = cursor.fetchall()
    for user in users:
        print(f"- User ID: {user[0]}")
        print(f"  Username: {user[1]}")
        print(f"  Email: {user[2]}")
        print(f"  Full Name: {user[3]}")
        print(f"  Active: {user[4]}")
        print(f"  Superuser: {user[5]}")
        print(f"  Created: {user[6]}")
        print()
    
    # Close cursor and connection
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc() 