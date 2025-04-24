from sqlalchemy import create_engine, text
import urllib.parse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    # Get PostgreSQL connection parameters
    user = os.getenv("POSTGRES_USER", "panashe")
    password = os.getenv("POSTGRES_PASSWORD", "panashe")
    server = os.getenv("POSTGRES_SERVER", "localhost") 
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "aiprojectmanagement")
    
    # Encode password to handle special characters
    encoded_password = urllib.parse.quote_plus(password)
    
    # Direct string concatenation to avoid any interpolation issues
    db_url = "postgresql://" + user + ":" + encoded_password + "@" + server + ":" + port + "/" + db
    
    print(f"Connecting to database: {db} as user: {user}")
    
    # Create engine
    engine = create_engine(db_url)
    
    # Create a connection
    with engine.connect() as conn:
        # List all users
        result = conn.execute(text("""
            SELECT id, username, email, full_name, is_active, is_superuser FROM users
        """))
        
        users = result.fetchall()
        
        if not users:
            print("No users found in the database!")
        else:
            print("\nAvailable Users:")
            print("----------------")
            for user in users:
                status = "Active" if user[4] else "Inactive"
                role = "Admin" if user[5] else "User"
                print(f"ID: {user[0]}, Username: {user[1]}, Name: {user[3]}, Status: {status}, Role: {role}")
        
        print("\nWhen creating a task, use one of these user IDs for the assignee_id field.")

if __name__ == "__main__":
    main() 