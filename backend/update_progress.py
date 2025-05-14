from sqlalchemy import create_engine, text
from database import DATABASE_URL

def update_progress():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("UPDATE tasks SET progress = 0.0 WHERE progress IS NULL;"))
        conn.commit()

if __name__ == "__main__":
    update_progress()
    print("Updated NULL progress values to 0.0") 