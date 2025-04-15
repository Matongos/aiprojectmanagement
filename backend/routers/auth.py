from fastapi import APIRouter, Body, Depends, HTTPException, Header, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
import services.auth_service as auth_service

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
__all__ = ["get_current_user", "router"]

# Create models for request bodies
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_superuser: Optional[bool] = False

# Create a router
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    print(f"Login attempt for user: {form_data.username}")
    
    # Use the auth service to authenticate
    try:
        user_data, error = auth_service.authenticate_user(db, form_data.username, form_data.password)
        
        if error:
            print(f"Authentication error: {error}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Login failed: {error}",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        print(f"Login successful for user: {form_data.username}")
        print(f"User details: {user_data}")
        
        return {
            "access_token": user_data["access_token"],
            "token_type": "bearer",
            "user": {
                "id": user_data["id"],
                "username": user_data["username"],
                "email": user_data["email"],
                "full_name": user_data["full_name"],
                "is_superuser": user_data["is_superuser"],
                "is_active": user_data.get("is_active", True),
                "profile_image_url": user_data.get("profile_image_url"),
                "job_title": user_data.get("job_title"),
                "bio": user_data.get("bio")
            }
        }
    except Exception as e:
        print(f"Login exception: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
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