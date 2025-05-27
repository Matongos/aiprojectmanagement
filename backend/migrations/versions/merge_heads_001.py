"""merge heads

Revision ID: merge_heads_001
Revises: add_time_entries_001, add_metrics_tables_006
Create Date: 2024-05-27 01:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads_001'
down_revision = ('add_time_entries_001', 'add_metrics_tables_006')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass 