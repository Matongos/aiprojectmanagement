from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from routers import auth

app = FastAPI(
    title="AI Project Management API",
    description="API for AI-Enhanced Project Management System",
    version="0.1.0"
)

# Configure CORS
origins = [
    "http://localhost:3000",  # Frontend URL (Next.js default)
    "http://localhost:8000",
    "http://localhost:8001",
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

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Project Management API!", "docs": "/docs"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Port 8001