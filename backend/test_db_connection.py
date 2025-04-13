import psycopg2
import urllib.parse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    try:
        # Get PostgreSQL connection parameters
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        server = os.getenv("POSTGRES_SERVER", "localhost") 
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "aiprojectmanagent")
        
        # Encode password to handle special characters
        encoded_password = urllib.parse.quote_plus(password)
        
        print(f"Testing connection to PostgreSQL database:")
        print(f"User: {user}")
        print(f"Password: {'*' * len(password)}")
        print(f"Server: {server}")
        print(f"Port: {port}")
        print(f"Database: {db}")
        
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            user=user,
            password=password,  # Use the original password, not the encoded one
            host=server,
            port=port,
            database=db
        )
        
        # If connection is successful
        cursor = conn.cursor()
        print("PostgreSQL connection is successful!")
        
        # Print PostgreSQL version
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        print(f"PostgreSQL server version: {db_version[0]}")
        
        # Close connection
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error connecting to PostgreSQL database: {e}")

if __name__ == "__main__":
    test_connection() 