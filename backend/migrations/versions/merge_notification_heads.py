"""merge notification heads

Revision ID: merge_notification_heads
Revises: rename_notification_type_column, update_notifications_table
Create Date: 2024-03-22 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'merge_notification_heads'
down_revision = None
branch_labels = None
depends_on = None

# Multiple revisions being merged
revises = ('rename_notification_type_column', 'update_notifications_table')

def upgrade() -> None:
    """Merge heads - no operation needed."""
    pass

def downgrade() -> None:
    """Downgrade - no operation needed."""
    pass 