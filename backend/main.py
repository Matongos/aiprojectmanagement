from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.openapi.utils import get_openapi
import uvicorn

# Import routers
from routers import auth, users

# Configure OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

app = FastAPI(
    title="AI Project Management API",
    description="API for AI-Enhanced Project Management System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security scheme to the OpenAPI schema
    openapi_schema["components"] = {
        "securitySchemes": {
            "OAuth2PasswordBearer": {
                "type": "oauth2",
                "flows": {
                    "password": {
                        "tokenUrl": "auth/login",
                        "scopes": {}
                    }
                }
            }
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [{"OAuth2PasswordBearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Configure CORS
origins = [
    "http://localhost:3000",  # Frontend URL (Next.js default)
    "http://localhost:8000",
    "http://localhost:8001",
    "http://localhost:8002",  # Add this new port
    "*"  # Allow all origins temporarily for debugging
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)

# Simple test endpoint directly in main.py
@app.get("/test-root")
def test_root():
    """Simple test endpoint at the application root"""
    return {"status": "OK", "message": "Root test endpoint works"}

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Project Management API!", "docs": "/docs"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)  # Changed port to 8003