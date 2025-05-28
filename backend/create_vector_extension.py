from sqlalchemy import create_engine, text
from config import settings

def create_vector_extension():
    try:
        # Create engine
        engine = create_engine(settings.DATABASE_URL)
        
        # Create vector extension
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            
            # Verify extension is created
            result = conn.execute(text("""
                SELECT * FROM pg_extension WHERE extname = 'vector';
            """))
            extensions = result.fetchall()
            
            if extensions:
                print("Vector extension successfully installed!")
            else:
                print("Failed to install vector extension")
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    create_vector_extension() 