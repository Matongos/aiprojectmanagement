from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import sys
import os
import urllib.parse
from dotenv import load_dotenv

# Add the parent directory to the Python path so we can import our models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all models to ensure they are registered
from models.base import Base
from models.ml_models import MLModel
from models.user import User
from models.project import Project
from models.task import Task
from models.milestone import Milestone
from models.tag import Tag
from models.activity import Activity
from models.comment import Comment
from models.metrics import ProjectMetrics, ResourceMetrics

# Load environment variables
load_dotenv()

# Get database connection parameters
user = os.getenv("POSTGRES_USER", "panashe")
password = os.getenv("POSTGRES_PASSWORD", "panashe")
host = os.getenv("POSTGRES_SERVER", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
database = os.getenv("POSTGRES_DB", "aiprojectmanagement")

# URL encode the password to handle special characters
encoded_password = urllib.parse.quote_plus(password)

# Create the database URL with encoded password
DATABASE_URL = f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}"

# Create base class for models
Base = declarative_base()

class MLModel(Base):
    """Stores ML model metadata and performance metrics"""
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    model_type = Column(String)  # e.g., "completion_time_predictor", "success_predictor"
    model_version = Column(String)
    performance_metrics = Column(JSON)  # Store model performance metrics
    hyperparameters = Column(JSON)  # Store model hyperparameters
    feature_importance = Column(JSON)  # Store feature importance scores
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_trained = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)

def init_ml_models():
    """Initialize ML models in the database"""
    engine = create_engine(DATABASE_URL)
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Check if we already have models initialized
        existing_models = db.query(MLModel).filter_by(is_active=True).all()
        if existing_models:
            print("ML models already initialized")
            return

        # Initialize completion time predictor model
        completion_predictor = MLModel(
            model_name="task_completion_predictor",
            model_type="completion_time_predictor",
            model_version="1.0.0",
            performance_metrics={
                "mae": 0.0,  # Mean Absolute Error
                "rmse": 0.0,  # Root Mean Square Error
                "r2": 0.0,   # R-squared score
            },
            hyperparameters={
                "n_estimators": 100,
                "max_depth": 10,
                "min_samples_split": 2,
            },
            feature_importance={},
            is_active=True
        )

        # Initialize success predictor model
        success_predictor = MLModel(
            model_name="task_success_predictor",
            model_type="success_predictor",
            model_version="1.0.0",
            performance_metrics={
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
            },
            hyperparameters={
                "n_estimators": 100,
                "max_depth": 8,
                "min_samples_split": 2,
            },
            feature_importance={},
            is_active=True
        )

        db.add(completion_predictor)
        db.add(success_predictor)
        db.commit()
        print("ML models initialized successfully")

    except Exception as e:
        print(f"Error initializing ML models: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_ml_models() 