"""Add email_notifications_enabled column to users table

Revision ID: 2023_add_email_notifications
Revises: add_notification_constraints
Create Date: 2023-11-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '2023_add_email_notifications'
down_revision = 'add_notification_constraints'  # Reference to the previous migration
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('email_notifications_enabled', sa.Boolean(), server_default='true', nullable=False))

def downgrade():
    op.drop_column('users', 'email_notifications_enabled') 