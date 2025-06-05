"""add task priority source

Revision ID: add_task_priority_source
Revises: 
Create Date: 2024-06-04 15:22:15.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_task_priority_source'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add priority_source column with default value 'auto'
    op.add_column('tasks', sa.Column('priority_source', sa.String(50), nullable=False, server_default='auto'))

def downgrade():
    # Remove priority_source column
    op.drop_column('tasks', 'priority_source') 