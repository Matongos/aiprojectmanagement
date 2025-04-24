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
        # Check if the column already exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tasks' AND column_name = 'assignee_id'
        """))
        
        if result.fetchone() is None:
            print("Column 'assignee_id' does not exist. Adding it now...")
            
            # Add the column
            conn.execute(text("""
                ALTER TABLE tasks 
                ADD COLUMN assignee_id INTEGER REFERENCES users(id)
            """))
            
            # Commit the transaction
            conn.commit()
            
            print("Column 'assignee_id' added successfully!")
        else:
            print("Column 'assignee_id' already exists.")

if __name__ == "__main__":
    main() 