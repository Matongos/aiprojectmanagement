from sqlalchemy import create_engine, text
from config import settings

def test_pgvector_setup():
    try:
        # Create engine using the correct settings attribute
        engine = create_engine(settings.DATABASE_URL)
        
        # Test connection and vector extension
        with engine.connect() as conn:
            # Check if vector extension exists
            result = conn.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
            extensions = result.fetchall()
            print("Vector extension status:", "Installed" if any(ext[1] == 'vector' for ext in extensions) else "Not installed")
            
            # Check if embeddings table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'embeddings'
                )
            """))
            table_exists = result.scalar()
            print("Embeddings table status:", "Exists" if table_exists else "Does not exist")
            
            # Test vector operations if extension is installed
            if any(ext[1] == 'vector' for ext in extensions):
                # Create a test vector
                conn.execute(text("CREATE TABLE IF NOT EXISTS vector_test (id serial primary key, vec vector(3))"))
                conn.execute(text("INSERT INTO vector_test (vec) VALUES ('[1,2,3]'::vector)"))
                print("Vector operations test: Successful")
            
            print("\nPgVector setup verification completed!")
            
    except Exception as e:
        print(f"Error during verification: {str(e)}")

if __name__ == "__main__":
    test_pgvector_setup() 