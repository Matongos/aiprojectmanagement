from sqlalchemy import create_engine, text

# Database connection URL
DATABASE_URL = "postgresql://panashe:panashe@localhost:5432/aiprojectmanagement"

def reset_alembic():
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Connect and reset alembic_version table
        with engine.connect() as connection:
            # Drop existing alembic_version table if it exists
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('base_tables_001')"))
            connection.commit()
            
        print("Successfully reset alembic version to base_tables_001!")
            
    except Exception as e:
        print(f"Error resetting alembic version: {str(e)}")

if __name__ == "__main__":
    reset_alembic() 