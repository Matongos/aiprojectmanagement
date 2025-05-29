"""merge heads

Revision ID: merge_heads_010
Revises: 89f67b23310c, combined_time_entries_001, update_notification_schema_009
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'merge_heads_010'
down_revision = ('89f67b23310c', 'combined_time_entries_001', 'update_notification_schema_009')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass 