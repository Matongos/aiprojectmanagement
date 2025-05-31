from sqlalchemy import create_engine, text
from models.base import Base
from models.user import User
from models.project import Project
from models.task import Task
from models.vector_embedding import VectorEmbedding
import os

# Get database URL from environment variable or use default
database_url = os.getenv('DATABASE_URL', 'postgresql://panashe:panashe@localhost:5432/aiprojectmanagement')

def setup_database():
    """Set up the database schema"""
    engine = create_engine(database_url)
    
    with engine.connect() as connection:
        # Drop schema with CASCADE
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
        connection.commit()
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    print("Database schema has been reset and recreated successfully!")

if __name__ == "__main__":
    setup_database() 