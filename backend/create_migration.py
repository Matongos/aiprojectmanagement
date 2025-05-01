import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from alembic.config import Config
from alembic import command

# Create Alembic configuration
alembic_cfg = Config("alembic.ini")

# Create a new migration
command.revision(alembic_cfg, autogenerate=True, message="update_task_model_fields") 