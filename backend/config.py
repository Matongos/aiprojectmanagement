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
    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS settings
    BACKEND_CORS_ORIGINS: list = ["*"]
    
    # Email settings
    EMAILS_ENABLED: bool = True
    
    # If using a service like Resend
    EMAIL_SERVICE: str = os.getenv("EMAIL_SERVICE", "smtp")  # smtp or resend
    RESEND_API_KEY: Optional[str] = os.getenv("RESEND_API_KEY", "")
    
    # Upload directory
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS: set = {"png", "jpg", "jpeg", "gif", "pdf", "doc", "docx", "xls", "xlsx"}
    
    # FastAPI-Mail settings
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "noreply@yourdomain.com")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "AI Project Management")
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # This allows extra fields to be present without validation errors


@lru_cache()
def get_settings():
    """Get application settings from cache."""
    return Settings()


settings = get_settings() 