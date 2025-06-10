"""add task complexity fields

Revision ID: add_task_complexity_fields
Revises: previous_revision
Create Date: 2024-03-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_task_complexity_fields'
down_revision = None  # Update this with the previous migration's revision ID
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to tasks table
    op.add_column('tasks', sa.Column('complexity_score', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('tasks', sa.Column('complexity_factors', postgresql.JSONB(), nullable=True, server_default='{}'))
    op.add_column('tasks', sa.Column('complexity_last_updated', sa.DateTime(timezone=True), nullable=True))

    # Create index for complexity_score for faster querying
    op.create_index('idx_tasks_complexity_score', 'tasks', ['complexity_score'])

def downgrade():
    # Remove added columns
    op.drop_index('idx_tasks_complexity_score')
    op.drop_column('tasks', 'complexity_last_updated')
    op.drop_column('tasks', 'complexity_factors')
    op.drop_column('tasks', 'complexity_score') 