"""rename notification type column

Revision ID: rename_notification_type_column
Revises: add_messages_table
Create Date: 2024-03-22 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'rename_notification_type_column'
down_revision = 'add_messages_table'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Rename type column to notification_type in notifications table."""
    op.alter_column('notifications', 'type',
                    new_column_name='notification_type',
                    existing_type=sa.String(50),
                    nullable=False)

def downgrade() -> None:
    """Revert the column name change."""
    op.alter_column('notifications', 'notification_type',
                    new_column_name='type',
                    existing_type=sa.String(50),
                    nullable=False) 