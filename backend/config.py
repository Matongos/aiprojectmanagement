import os
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    PROJECT_NAME: str = "AI Project Management"
    
    # Database settings
    DATABASE_URL: str = "postgresql://panashe:panashe@localhost:5432/aiprojectmanagement"
    
    # JWT settings
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS settings
    BACKEND_CORS_ORIGINS: list = ["*"]
    
    # Email settings
    EMAILS_ENABLED: bool = True
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = 587
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD", "")
    EMAILS_FROM_EMAIL: Optional[str] = os.getenv("EMAILS_FROM_EMAIL", "noreply@aiprojectmanagement.com")
    EMAILS_FROM_NAME: Optional[str] = os.getenv("EMAILS_FROM_NAME", "AI Project Management")
    
    # If using a service like Resend
    EMAIL_SERVICE: str = os.getenv("EMAIL_SERVICE", "smtp")  # smtp or resend
    RESEND_API_KEY: Optional[str] = os.getenv("RESEND_API_KEY", "")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # This allows extra fields to be present without validation errors


@lru_cache()
def get_settings():
    """Get application settings from cache."""
    return Settings()


settings = get_settings() 