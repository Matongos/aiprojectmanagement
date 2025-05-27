"""base tables

Revision ID: base_tables_001
Create Date: 2024-03-20 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'base_tables_001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # These tables already exist, this is just for Alembic to track the schema
    pass

def downgrade():
    pass 