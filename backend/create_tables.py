from database import Base, engine
from models.task import Task  # This will import all other models through dependencies

def create_tables():
    print("Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

if __name__ == "__main__":
    create_tables() 