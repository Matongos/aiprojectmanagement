from fastapi import FastAPI, Request, Depends, status, Body, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from routers import auth, users, roles, projects, tasks, analytics, file_attachments, activities, comments, notifications, task_stages, stages, permissions, milestones, tags, log_notes, time_entries, messages, vectors, ai, websockets, followers, ai_router, weather, task_complexity, task_priority, task_analysis
from database import engine, Base, create_tables
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import get_db
import requests
from typing import Optional
from starlette.staticfiles import StaticFiles
from services.task_scheduler import TaskScheduler
from config import settings
from contextlib import asynccontextmanager
import bcrypt
from passlib.context import CryptContext
import asyncio
from workers.task_scheduler import start_scheduler
from workers.metrics_worker import start_metrics_worker
from services.scheduler_service import scheduler_service
import logging

# Create bcrypt context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
print("Successfully initialized bcrypt CryptContext")

# Create database tables
print(f"Created direct database engine with URL: {str(engine.url)}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    create_tables()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="AI Project Management API",
    description="API for managing projects and tasks with AI assistance",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_version="3.0.2",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(tags.router)
app.include_router(log_notes.router)
app.include_router(time_entries.router)
app.include_router(messages.router)
app.include_router(vectors.router)
app.include_router(ai_router.router)
app.include_router(websockets.router)
app.include_router(followers.router)
app.include_router(weather.router)
app.include_router(task_complexity.router)
app.include_router(task_priority.router)
app.include_router(task_analysis.router)

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

@app.on_event("startup")
async def startup_event():
    """Start background tasks when the application starts"""
    # Start task scheduler in the background
    asyncio.create_task(start_scheduler())
    # Start metrics worker in the background
    asyncio.create_task(start_metrics_worker())
    # Start weather cache update loop
    from services.weather_cache_service import get_weather_cache_service
    weather_cache = get_weather_cache_service()
    asyncio.create_task(weather_cache.start_weather_update_loop())
    # Start the scheduler when the application starts
    try:
        await scheduler_service.start()
        logger.info("Task priority scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start task priority scheduler: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the scheduler when the application shuts down"""
    try:
        await scheduler_service.stop()
        logger.info("Task priority scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop task priority scheduler: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)