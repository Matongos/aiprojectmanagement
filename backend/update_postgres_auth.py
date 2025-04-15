import psycopg2
import sys
import subprocess
import os

# First, try to connect as superuser postgres
try:
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        dbname='postgres',
        user='postgres',
        password='postgres',  # Assuming this is your postgres superuser password
        host='localhost',
        port=5432
    )
    
    # Set autocommit mode
    conn.autocommit = True
    
    # Create a cursor
    cur = conn.cursor()
    
    print("Successfully connected as postgres user")
    
    # Reset the password for panashe user
    cur.execute("ALTER USER panashe WITH PASSWORD 'panashe';")
    print("Password for user 'panashe' has been updated")
    
    # Grant all privileges on database to panashe
    cur.execute("GRANT ALL PRIVILEGES ON DATABASE aiprojectmanagement TO panashe;")
    print("Granted privileges on aiprojectmanagement database to panashe")
    
    # Close connection
    cur.close()
    conn.close()
    
    print("PostgreSQL user permissions updated successfully!")
    
except Exception as e:
    print(f"Error with postgres superuser: {e}")
    
# Now try to connect with the updated credentials
try:
    # Connect to PostgreSQL with the new credentials
    conn = psycopg2.connect(
        dbname='aiprojectmanagement',
        user='panashe',
        password='panashe',
        host='localhost',
        port=5432
    )
    
    print("Successfully connected with user 'panashe'")
    conn.close()
    
except Exception as e:
    print(f"Failed to connect with updated credentials: {e}")

print("\nTrying to connect via psql command line...")

# Try using psql command (for Windows)
try:
    # Run psql command to test connection
    cmd = 'psql "postgresql://panashe:panashe@localhost:5432/aiprojectmanagement" -c "SELECT current_user, current_database();"'
    os.system(cmd)
    
except Exception as e:
    print(f"Failed to run psql command: {e}") 