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
        # List all projects
        result = conn.execute(text("""
            SELECT id, name, description, status FROM projects
        """))
        
        projects = result.fetchall()
        
        if not projects:
            print("No projects found in the database!")
            print("Let's create a sample project:")
            
            # Create a sample project
            conn.execute(text("""
                INSERT INTO projects (name, description, status, created_by)
                VALUES ('Sample Project', 'A sample project for testing', 'active', 8)
            """))
            
            conn.commit()
            
            print("Sample project created! Running query again...")
            
            # List again
            result = conn.execute(text("""
                SELECT id, name, description, status FROM projects
            """))
            
            projects = result.fetchall()
        
        print("\nAvailable Projects:")
        print("-------------------")
        for project in projects:
            print(f"ID: {project[0]}, Name: {project[1]}, Status: {project[3]}")
        
        print("\nWhen creating a task, use one of these project IDs for the project_id field.")

if __name__ == "__main__":
    main() 