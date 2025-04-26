"""add notification constraints

Revision ID: add_notification_constraints
Revises: add_activities_table
Create Date: 2023-11-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_notification_constraints'
down_revision = 'add_activities_table'
branch_labels = None
depends_on = None


def upgrade():
    # Create unique index on user_id, reference_type, reference_id, and type to prevent duplicate notifications
    op.create_index(
        'ix_notifications_unique_reference', 
        'notifications', 
        ['user_id', 'reference_type', 'reference_id', 'type'], 
        unique=True,
        postgresql_where=sa.text("reference_id IS NOT NULL AND reference_type IS NOT NULL")
    )


def downgrade():
    op.drop_index('ix_notifications_unique_reference', table_name='notifications') 