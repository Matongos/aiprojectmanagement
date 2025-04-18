from database import engine, Base, SessionLocal
import models  # This imports all your models
import sys
from services.auth_service import register_user
from sqlalchemy import inspect

def create_admin_user(username: str, password: str, email: str, full_name: str):
    """Create a new admin user."""
    try:
        print(f"\n=== Creating Admin User ===")
        print(f"Username: {username}")
        print(f"Email: {email}")
        print(f"Full Name: {full_name}")
        
        db = SessionLocal()
        try:
            # Register the user with admin privileges
            user_data, error = register_user(
                db=db,
                email=email,
                username=username,
                full_name=full_name,
                password=password,
                is_superuser=True
            )
            
            if error:
                print(f"❌ Error creating admin user: {error}")
                return False
                
            print(f"✅ Admin user created successfully!")
            print(f"User ID: {user_data['id']}")
            print(f"Username: {user_data['username']}")
            print(f"Email: {user_data['email']}")
            print(f"Full Name: {user_data['full_name']}")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        return False

def main():
    try:
        print("Connecting to existing database...")
        print("Creating tables if they don't exist...")
        
        # Create tables
        Base.metadata.create_all(engine)
        
        print("Connection successful and tables created!")
        
        # Count and list tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Database contains {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
            
        return True
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    # Create a new admin user
    create_admin_user(
        username="admin2",
        password="admin123",
        email="admin2@example.com",
        full_name="Admin User 2"
    )
    
    success = main()
    if not success:
        sys.exit(1) 