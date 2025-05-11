from fastapi import FastAPI, Request, Depends, status, Body, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from routers import auth, users, roles, projects, tasks, analytics, file_attachments, activities, comments, notifications, task_stages, stages, permissions, milestones
from database import engine, Base
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import get_db
import requests
from typing import Optional
from starlette.staticfiles import StaticFiles
from services.task_scheduler import TaskScheduler
from config import settings

# Create database tables
Base.metadata.create_all(bind=engine)

# Create OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

app = FastAPI(
    title="AI Project Management API",
    description="API for managing projects and tasks with AI assistance",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_version="3.0.2"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["*"],  # Expose all headers
    max_age=600,  # How long the results of a preflight request can be cached
)

# Mount static files
# Serving uploads directory for file downloads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(analytics.router)
app.include_router(file_attachments.router)
app.include_router(activities.router)
app.include_router(comments.router)
app.include_router(notifications.router)
app.include_router(task_stages.router)
app.include_router(stages.router)
app.include_router(permissions.router)
app.include_router(milestones.router)

# Add a simplified token endpoint
@app.post("/token")
async def token_endpoint(
    username: str = Form(...), 
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Simple token endpoint that only requires username and password.
    
    Parameters:
    - **username**: Your username
    - **password**: Your password
    
    Returns a token and user information.
    """
    try:
        print("\n=== /token Endpoint Called ===")
        print(f"Username: {username}")
        print(f"Password length: {len(password) if password else 0} chars")
        
        # Get user from database
        user = db.query(auth.User).filter(auth.User.username == username).first()
        
        if not user:
            print(f"❌ User not found: {username}")
            raise auth.HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        print(f"✅ User found: {user.username}, is_active: {user.is_active}")
        
        # If user is inactive
        if not user.is_active:
            print("❌ User is inactive")
            raise auth.HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        password_verified = auth.auth_service.verify_password(password, user.hashed_password)
        print(f"Password verification: {'✅ Success' if password_verified else '❌ Failed'}")
        
        if not password_verified:
            raise auth.HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = auth.timedelta(minutes=auth.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.auth_service.create_access_token(
            data={"sub": user.username, "id": user.id},
            expires_delta=access_token_expires
        )
        
        print("✅ Token created successfully")
        
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
    except Exception as e:
        print(f"❌ Error in token endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="AI Project Management API",
        version="1.0.0",
        description="API for managing projects and tasks with AI assistance",
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token in the format: Bearer <token>"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [{"OAuth2PasswordBearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Project Management API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == "__main__":
    # Start the task scheduler
    TaskScheduler.start_scheduler()
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)