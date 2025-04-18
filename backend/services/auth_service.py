from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
from jose import jwt
import os
from dotenv import load_dotenv
import traceback
import urllib.parse
from fastapi import HTTPException
from models.users import User

# Load environment variables
load_dotenv()

# Password hashing - with fallback for bcrypt issues
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    print("Successfully initialized bcrypt CryptContext")
except Exception as e:
    print(f"Error initializing bcrypt CryptContext: {e}")
    # Fallback to a simpler context if bcrypt fails
    pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
    print("Fallback to sha256_crypt successful")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET", "development_secret_please_change_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create a direct engine for database operations - use environment variables
try:
    # Get database connection parameters
    user = os.getenv("POSTGRES_USER", "panashe")
    password = os.getenv("POSTGRES_PASSWORD", "panashe")  # Make sure the default is 'panashe'
    host = os.getenv("POSTGRES_SERVER", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "aiprojectmanagement")
    
    # URL encode the password to handle special characters
    encoded_password = urllib.parse.quote_plus(password)
    
    # Create the database URL with encoded password
    DATABASE_URL = f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}"
    direct_engine = create_engine(DATABASE_URL)
    print(f"Created direct database engine with URL: {DATABASE_URL}")
except Exception as e:
    print(f"Error creating direct database engine: {e}")
    direct_engine = None

def verify_password(plain_password, hashed_password):
    """Verify a password against a hash."""
    try:
        print(f"\n=== Password Verification ===")
        print(f"Plain password: {plain_password}")
        print(f"Hashed password: {hashed_password[:10]}...")
        
        result = pwd_context.verify(plain_password, hashed_password)
        print(f"Verification result: {'✅ Success' if result else '❌ Failed'}")
        
        if not result:
            print("❌ Password verification failed")
            # Try to hash the plain password to see if it matches
            test_hash = pwd_context.hash(plain_password)
            print(f"Test hash of plain password: {test_hash[:10]}...")
            print(f"Hash comparison: {'✅ Matches' if test_hash == hashed_password else '❌ Does not match'}")
            
        return result
    except Exception as e:
        print(f"❌ Password verification error: {e}")
        traceback.print_exc()
        return False

def get_password_hash(password):
    """Generate a password hash."""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        print(f"Password hashing error: {e}")
        # Return a clear error that can be caught
        raise ValueError(f"Could not hash password: {e}")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def register_user(db: Session, email: str, username: str, full_name: str, password: str, is_superuser: bool = False) -> Tuple[Optional[Dict], Optional[str]]:
    """Register a new user."""
    try:
        print(f"Registering new user: {username}")
        
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            print(f"User already exists: {username}")
            return None, "Username or email already exists"
        
        # Hash the password
        print(f"Hashing password for user: {username}")
        hashed_password = get_password_hash(password)
        print(f"Generated hash for user {username}: {hashed_password}")
        
        # Create new user
        new_user = User(
            email=email,
            username=username,
            full_name=full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=is_superuser
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"Successfully created user: {username}")
        
        return {
            "id": new_user.id,
            "email": new_user.email,
            "username": new_user.username,
            "full_name": new_user.full_name,
            "is_active": new_user.is_active,
            "is_superuser": new_user.is_superuser
        }, None
        
    except Exception as e:
        db.rollback()
        print(f"Error registering user: {str(e)}")
        traceback.print_exc()
        return None, str(e)

async def authenticate_user(db: Session, username: str, password: str):
    """Authenticate a user and return user data with access token."""
    try:
        print(f"\n=== Authentication Attempt ===")
        print(f"Username: {username}")
        
        # Find user with username and check if they are active
        user = db.query(User).filter(
            User.username == username,
            User.is_active == True
        ).first()
        
        if not user:
            print(f"❌ User not found or inactive: {username}")
            return None, "Incorrect username or password"
            
        print(f"✅ User found: {user.username}")
        print(f"  - Is Active: {user.is_active}")
        print(f"  - Hashed Password: {user.hashed_password[:10]}...")
        
        try:
            # Verify password
            if not verify_password(password, user.hashed_password):
                print(f"❌ Password verification failed for user: {username}")
                return None, "Incorrect username or password"
                
            print(f"✅ Password verified successfully")
            
            # Create access token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user.username, "id": user.id},
                expires_delta=access_token_expires
            )
            
            print(f"✅ Access token created successfully")
            
            # Return user data without hashed_password
            user_data = {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "is_superuser": user.is_superuser,
                    "profile_image_url": user.profile_image_url,
                    "job_title": user.job_title,
                    "bio": user.bio
                }
            }
            return user_data, None
            
        except Exception as e:
            print(f"❌ Error during authentication: {str(e)}")
            traceback.print_exc()
            return None, "Authentication failed"
        
    except Exception as e:
        print(f"❌ Authentication error: {str(e)}")
        traceback.print_exc()
        return None, "Authentication failed"

def get_user_by_id(db: Session, user_id: int):
    """Get a user by ID."""
    try:
        query = text("""
            SELECT id, username, email, full_name, is_active, is_superuser,
                   profile_image_url, job_title, bio
            FROM users 
            WHERE id = :id
        """)
        result = db.execute(query, {"id": user_id}).fetchone()
        
        if not result:
            return None
            
        return {
            "id": result[0],
            "username": result[1],
            "email": result[2],
            "full_name": result[3],
            "is_active": result[4],
            "is_superuser": result[5],
            "profile_image_url": result[6],
            "job_title": result[7],
            "bio": result[8]
        }
    except Exception as e:
        print(f"Error getting user by ID: {str(e)}")
        return None

def get_user_from_token(token: str, db: Session):
    """Validate a JWT token and return the user."""
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user_id = payload.get("id")
        
        if username is None or user_id is None:
            return None
        
        # Get the user from database
        try:
            # Try with the ORM session - use text() properly
            query = text("SELECT id, username, email, full_name, is_active, is_superuser FROM users WHERE id = :id")
            result = db.execute(query, {"id": user_id}).fetchone()
            
            if result:
                user = {
                    "id": result[0],
                    "username": result[1],
                    "email": result[2],
                    "full_name": result[3],
                    "is_active": result[4],
                    "is_superuser": result[5]
                }
                return user
        
        except Exception as orm_error:
            print(f"ORM session error getting user from token: {str(orm_error)}")
            
            # Try with direct connection if ORM fails
            if direct_engine:
                try:
                    with direct_engine.connect() as direct_conn:
                        query = text("SELECT id, username, email, full_name, is_active, is_superuser FROM users WHERE id = :id")
                        result = direct_conn.execute(query, {"id": user_id}).fetchone()
                        
                        if result:
                            user = {
                                "id": result[0],
                                "username": result[1],
                                "email": result[2],
                                "full_name": result[3],
                                "is_active": result[4],
                                "is_superuser": result[5]
                            }
                            return user
                except Exception as direct_error:
                    print(f"Direct connection error getting user from token: {str(direct_error)}")
        
        return None
    
    except jwt.JWTError:
        return None
    except Exception as e:
        print(f"Error getting user from token: {str(e)}")
        return None

def test_database_connection():
    """Test database connection and return diagnostics."""
    try:
        if not direct_engine:
            return {"status": "ERROR", "message": "No direct engine available"}
            
        with direct_engine.connect() as conn:
            # Test simple query
            result = conn.execute(text("SELECT 1 as test")).fetchone()
            
            if result:
                # Get database info
                version = conn.execute(text("SELECT version()")).fetchone()
                
                # List tables
                tables = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)).fetchall()
                
                table_list = [table[0] for table in tables]
                
                return {
                    "status": "OK",
                    "test_query": result[0],
                    "version": version[0] if version else None,
                    "tables_count": len(table_list),
                    "tables": table_list,
                    "message": "Database connection successful"
                }
            
            return {"status": "ERROR", "message": "Query execution failed"}
            
    except Exception as e:
        traceback.print_exc()
        return {
            "status": "ERROR",
            "message": f"Database connection failed: {str(e)}"
        }

def decode_token(token: str):
    """Decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.JWTError as e:
        raise HTTPException(status_code=401, detail=f"Could not validate credentials: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation error: {str(e)}") 