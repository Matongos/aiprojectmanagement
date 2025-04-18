from fastapi import APIRouter, Body, Depends, HTTPException, Header, status, Form, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import traceback
from datetime import datetime, timedelta

from database import get_db
from services import auth_service
from models.users import User

# Create OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Function to get current user from token
async def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """Get the current user from the JWT token."""
    try:
        # Decode the token
        payload = auth_service.decode_token(token)
        username = payload.get("sub")
        user_id = payload.get("id")
        
        if not username or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Get user from database
        user = auth_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

# Export the get_current_user function explicitly
__all__ = ["get_current_user", "router", "oauth2_scheme"]

# Create models for request bodies
class LoginRequest(BaseModel):
    username: str = Field(..., description="Your username", examples=["testuser123"])
    password: str = Field(..., description="Your password", examples=["testpassword123"])

class RegisterRequest(BaseModel):
    username: str = Field(..., description="Desired username", examples=["newuser"])
    password: str = Field(..., description="Desired password", examples=["strongpassword123"])
    email: Optional[str] = Field(None, description="Email address", examples=["user@example.com"])
    full_name: Optional[str] = Field(None, description="Full name", examples=["New User"])
    is_superuser: Optional[bool] = Field(False, description="Whether user is superuser", examples=[False])

class UserResponse(BaseModel):
    id: int = Field(..., description="User ID", examples=[1])
    username: str = Field(..., description="Username", examples=["testuser123"])
    email: str = Field(..., description="Email address", examples=["user@example.com"])
    full_name: str = Field(..., description="Full name", examples=["Test User"])
    is_superuser: bool = Field(..., description="Whether user is superuser", examples=[False])
    is_active: bool = Field(..., description="Whether user is active", examples=[True])
    profile_image_url: Optional[str] = Field(None, description="Profile image URL", examples=["https://example.com/profile.jpg"])
    job_title: Optional[str] = Field(None, description="Job title", examples=["Software Developer"])
    bio: Optional[str] = Field(None, description="User bio", examples=["A passionate developer"])

class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = Field(..., description="Token type", examples=["bearer"])
    user: UserResponse

class RegisterResponse(BaseModel):
    id: int = Field(..., description="User ID", examples=[1])
    username: str = Field(..., description="Username", examples=["newuser"])
    email: str = Field(..., description="Email address", examples=["user@example.com"])
    full_name: str = Field(..., description="Full name", examples=["New User"])
    is_superuser: bool = Field(..., description="Whether user is superuser", examples=[False])
    is_active: bool = Field(..., description="Whether user is active", examples=[True])

# Create a router
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return access token.
    
    Args:
        login_data: LoginRequest containing username and password
        db: Database session
        
    Returns:
        LoginResponse with access token and user details
    """
    try:
        print(f"\n=== Login Attempt ===")
        print(f"Username: {login_data.username}")
        
        # First check if user exists
        user = db.query(User).filter(User.username == login_data.username).first()
        if not user:
            print(f"❌ User not found: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
            
        print(f"✅ User found: {user.username}")
        print(f"User is active: {user.is_active}")
        
        if not user.is_active:
            print("❌ User is inactive")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
            
        # Verify password
        if not auth_service.verify_password(login_data.password, user.hashed_password):
            print("❌ Password verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
            
        print("✅ Password verified successfully")
        
        # Create access token
        access_token_expires = timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": user.username, "id": user.id},
            expires_delta=access_token_expires
        )
        
        # Return user data and token
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_superuser": user.is_superuser,
                "is_active": user.is_active,
                "profile_image_url": user.profile_image_url,
                "job_title": user.job_title,
                "bio": user.bio
            }
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during login: {str(e)}"
        )

@router.post(
    "/register",
    response_model=RegisterResponse,
    responses={
        200: {
            "description": "Successful registration",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "newuser",
                        "email": "user@example.com",
                        "full_name": "New User",
                        "is_superuser": False,
                        "is_active": True
                    }
                }
            }
        },
        400: {"description": "Bad request"},
        422: {"description": "Validation error"}
    }
)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register endpoint with database connection."""
    print(f"Registering new user: {request.username}")
    
    try:
        # Test DB connection first
        test_result = db.execute(text("SELECT 1 as test")).fetchone()
        print(f"DB connection test result: {test_result}")
    except Exception as db_test_error:
        print(f"DB connection test failed: {db_test_error}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(db_test_error)}")
    
    # Use provided email or generate one
    user_email = request.email if request.email else f"{request.username}@example.com"
    
    # Use provided full name or generate one
    user_full_name = request.full_name if request.full_name else f"New User {request.username}"
    
    print(f"Register endpoint - using email: {user_email}, username: {request.username}, full_name: {user_full_name}, is_superuser: {request.is_superuser}")
    
    try:
        # Register the user using the auth service
        user_data, error = auth_service.register_user(
            db, 
            email=user_email,
            username=request.username,
            full_name=user_full_name,
            password=request.password,
            is_superuser=request.is_superuser
        )
        
        if error:
            print(f"Registration error: {error}")
            raise HTTPException(status_code=400, detail=f"Registration failed: {error}")
            
        return user_data
    except Exception as e:
        print(f"Registration exception in endpoint: {e}")
        import traceback
        traceback.print_exc()
        
        # Return comprehensive error
        error_detail = {
            "error": str(e),
            "type": str(type(e).__name__),
            "message": "Registration failed - see server logs for details"
        }
        
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("/test")
async def test_endpoint():
    """Test endpoint without database connection."""
    return JSONResponse({"status": "OK", "message": "Test endpoint works"})

@router.get("/test-db")
async def test_db_endpoint(db: Session = Depends(get_db)):
    """Test endpoint that checks database connection."""
    try:
        # Try to execute a simple query with proper SQLAlchemy syntax
        result = db.execute(text("SELECT 1 as test")).fetchone()
        
        return JSONResponse({
            "status": "OK",
            "message": "Database connection successful",
            "result": result[0] if result else None
        })
    except Exception as e:
        print(f"Database connection error: {e}")
        return JSONResponse({
            "status": "ERROR",
            "message": f"Database connection failed: {str(e)}"
        }, status_code=500) 