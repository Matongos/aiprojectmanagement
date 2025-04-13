from sqlalchemy.orm import Session
from sqlalchemy import text
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt

# Password hashing
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception as e:
    print(f"Error initializing CryptContext: {e}")
    # Fallback to a simpler context if bcrypt fails
    pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# JWT settings
SECRET_KEY = "your-secret-key"  # Replace with a secure secret key in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password, hashed_password):
    """Verify a password against a hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        # Simple fallback check (not for production)
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

def register_user(db: Session, email: str, username: str, full_name: str, password: str):
    """Register a new user directly using SQL queries to avoid ORM relationship issues."""
    try:
        # Check if user already exists
        check_query = text("SELECT id FROM users WHERE username = :username OR email = :email")
        existing_user = db.execute(check_query, {"username": username, "email": email}).fetchone()
        
        if existing_user:
            return None, "Username or email already registered"
        
        # Hash the password
        hashed_password = get_password_hash(password)
        
        # Insert new user
        insert_query = text("""
        INSERT INTO users (email, username, full_name, hashed_password, is_active, is_superuser, created_at, updated_at) 
        VALUES (:email, :username, :full_name, :hashed_password, :is_active, :is_superuser, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id, email, username, full_name, is_active, is_superuser
        """)
        
        result = db.execute(
            insert_query, 
            {
                "email": email,
                "username": username,
                "full_name": full_name,
                "hashed_password": hashed_password,
                "is_active": True,
                "is_superuser": False
            }
        ).fetchone()
        
        db.commit()
        
        # Create the user dictionary
        user = {
            "id": result[0],
            "email": result[1],
            "username": result[2],
            "full_name": result[3],
            "is_active": result[4],
            "is_superuser": result[5]
        }
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username, "id": user["id"]},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "is_superuser": user["is_superuser"]
        }, None
        
    except Exception as e:
        db.rollback()
        return None, str(e)

def authenticate_user(db: Session, username: str, password: str):
    """Authenticate a user."""
    try:
        print(f"Authenticating user: {username}")
        # Find user with username
        query = text("SELECT id, username, email, full_name, hashed_password, is_active, is_superuser FROM users WHERE username = :username")
        result = db.execute(query, {"username": username}).fetchone()
        
        if not result:
            print(f"User not found: {username}")
            return None, "User not found"
        
        user = {
            "id": result[0],
            "username": result[1],
            "email": result[2],
            "full_name": result[3],
            "hashed_password": result[4],
            "is_active": result[5],
            "is_superuser": result[6]
        }
        
        print(f"Verifying password for user: {username}")
        if not verify_password(password, user["hashed_password"]):
            print(f"Incorrect password for user: {username}")
            return None, "Incorrect password"
            
        if not user["is_active"]:
            print(f"Inactive user: {username}")
            return None, "Inactive user"
            
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["username"], "id": user["id"]},
            expires_delta=access_token_expires
        )
        
        print(f"Authentication successful for user: {username}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "is_superuser": user["is_superuser"]
        }, None
        
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        return None, str(e)

def get_user_by_id(db: Session, user_id: int):
    """Get a user by ID."""
    try:
        query = text("SELECT id, username, email, full_name, is_active, is_superuser FROM users WHERE id = :id")
        result = db.execute(query, {"id": user_id}).fetchone()
        
        if not result:
            return None
            
        return {
            "id": result[0],
            "username": result[1],
            "email": result[2],
            "full_name": result[3],
            "is_active": result[4],
            "is_superuser": result[5]
        }
    except Exception:
        return None 