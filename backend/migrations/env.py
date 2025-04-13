from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import create_engine

from alembic import context

import os
import sys
from dotenv import load_dotenv
import urllib.parse

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the SQLAlchemy declarative base and models
from database import Base
import models

# Load environment variables
load_dotenv()

# Get environment variables
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "aiprojectmanagent")

# Create database URL based on environment
if ENVIRONMENT == "development":
    # Use SQLite for development
    SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"
else:
    # Use PostgreSQL for production
    # Encode password to handle special characters
    quoted_password = urllib.parse.quote_plus(POSTGRES_PASSWORD)
    
    # Direct string concatenation to avoid interpolation issues
    SQLALCHEMY_DATABASE_URL = "postgresql://" + POSTGRES_USER + ":" + quoted_password + "@" + POSTGRES_SERVER + ":" + POSTGRES_PORT + "/" + POSTGRES_DB

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set raw sqlalchemy.url in alembic config
# The key here is to use set_section_option instead of set_main_option
config.set_section_option(config.config_ini_section, "sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Instead of using config.get_main_option, we'll use our manually created URL
    # Get environment variables
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    server = os.getenv("POSTGRES_SERVER", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "aiprojectmanagent")
    
    # URL encode the password to handle special characters
    encoded_password = urllib.parse.quote_plus(password)
    
    # Create the database URL with manual string concatenation
    url = "postgresql://" + user + ":" + encoded_password + "@" + server + ":" + port + "/" + db

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Instead of using config to create the engine, we'll create it directly
    # Get environment variables
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    server = os.getenv("POSTGRES_SERVER", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "aiprojectmanagent")
    
    # URL encode the password to handle special characters
    encoded_password = urllib.parse.quote_plus(password)
    
    # Create the database URL with manual string concatenation
    url = "postgresql://" + user + ":" + encoded_password + "@" + server + ":" + port + "/" + db
    
    # Create the engine directly
    engine = create_engine(url)

    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
