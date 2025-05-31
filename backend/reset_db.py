from sqlalchemy import text
from database import engine

def reset_migrations():
    with engine.connect() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        connection.execute(text("DROP TABLE IF EXISTS vector_embeddings"))
        print("Successfully reset migration state")

if __name__ == "__main__":
    reset_migrations() 