"""update notifications table

Revision ID: update_notifications_table
Revises: add_messages_table
Create Date: 2024-03-22 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = 'update_notifications_table'
down_revision = 'add_messages_table'
branch_labels = None
depends_on = None

# Define notification types
notification_types = [
    'task_assignment',
    'task_update',
    'task_comment',
    'task_mention',
    'message',
    'project_update',
    'milestone_update',
    'system',
    'deadline_reminder',
    'log_note'
]

def upgrade() -> None:
    """Update notifications table with new column and constraints."""
    
    # First, update any existing notifications to use a valid type
    op.execute("""
        UPDATE notifications 
        SET type = 'system' 
        WHERE type NOT IN (
            'task_assignment', 'task_update', 'task_comment', 'task_mention',
            'message', 'project_update', 'milestone_update', 'system',
            'deadline_reminder', 'log_note'
        )
    """)
    
    # Create an enum type for notification types
    notification_type_enum = postgresql.ENUM(*notification_types, name='notification_type_enum')
    notification_type_enum.create(op.get_bind())
    
    # Add check constraint to ensure only valid notification types are used
    op.create_check_constraint(
        'notification_type_check',
        'notifications',
        f"type = ANY(ARRAY{notification_types})"
    )
    
    # Add index for faster querying
    op.create_index(
        'ix_notifications_type',
        'notifications',
        ['type']
    )

def downgrade() -> None:
    """Revert changes to notifications table."""
    
    # Drop the check constraint
    op.drop_constraint('notification_type_check', 'notifications')
    
    # Drop the index
    op.drop_index('ix_notifications_type')
    
    # Drop the enum type
    op.execute('DROP TYPE notification_type_enum') 