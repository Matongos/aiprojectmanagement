from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os

class Settings(BaseSettings):
    # Environment
    environment: str = "development"
    log_level: str = "DEBUG"

    # Database settings
    postgres_user: str = "panashe"
    postgres_password: str = "panashe"
    postgres_server: str = "localhost"
    postgres_port: str = "5432"
    postgres_db: str = "aiprojectmanagement"
    DATABASE_URL: str = "postgresql://panashe:panashe@localhost:5432/aiprojectmanagement"
    
    # Email settings
    MAIL_USERNAME: str = "panahsematongo7@gmail.com"
    MAIL_PASSWORD: str = "matongo@123@"
    MAIL_FROM: str = "panahsematongo7@gmail.com"
    MAIL_FROM_NAME: str = "AI Project Management"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    
    # File Upload settings
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list = ["pdf", "png", "jpg", "jpeg", "doc", "docx", "txt"]
    
    # JWT settings
    jwt_secret: str = "development_secret_please_change_in_production"
    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # Weather settings
    OPENWEATHER_API_KEY: str = "56dbce1abd3adbaeef3ad878a0be6c1f"
    DEFAULT_CITY: str = "London"
    WEATHER_UPDATE_INTERVAL: int = 1800  # 30 minutes in seconds
    WEATHER_RISK_THRESHOLD: float = 0.3
    HEAVY_RAIN_THRESHOLD: float = 10.0
    MODERATE_RAIN_THRESHOLD: float = 2.0
    STRONG_WIND_THRESHOLD: float = 10.0
    MODERATE_WIND_THRESHOLD: float = 7.0
    HIGH_TEMP_THRESHOLD: float = 35.0
    LOW_TEMP_THRESHOLD: float = 0.0
    MODERATE_HIGH_TEMP_THRESHOLD: float = 30.0
    MODERATE_LOW_TEMP_THRESHOLD: float = 5.0

    class Config:
        env_file = ".env"
        extra = "allow"  # This will allow extra fields from env without raising validation errors

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create upload directory if it doesn't exist
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        # Create subdirectories for different upload types
        os.makedirs(os.path.join(self.UPLOAD_DIR, "log_notes"), exist_ok=True)
        os.makedirs(os.path.join(self.UPLOAD_DIR, "attachments"), exist_ok=True)

@lru_cache()
def get_settings() -> Settings:
    return Settings() 