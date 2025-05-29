"""update notification schema

Revision ID: update_notification_schema_009
Revises: add_project_role_enum_008
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'update_notification_schema_009'
down_revision = 'add_project_role_enum_008'
branch_labels = None
depends_on = None

def upgrade():
    # Make content column nullable
    op.alter_column('notifications', 'content',
               existing_type=sa.Text(),
               nullable=True)
    
    # Rename notification_type column to type
    op.alter_column('notifications', 'notification_type',
               new_column_name='type',
               existing_type=sa.String(50),
               nullable=False)

def downgrade():
    # Make content column non-nullable
    op.alter_column('notifications', 'content',
               existing_type=sa.Text(),
               nullable=False)
    
    # Rename type column back to notification_type
    op.alter_column('notifications', 'type',
               new_column_name='notification_type',
               existing_type=sa.String(50),
               nullable=False) 