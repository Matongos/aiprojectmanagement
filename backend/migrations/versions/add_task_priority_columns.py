"""Add task priority columns

Revision ID: add_task_priority_columns
Revises: 2023_06_03_001
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = 'add_task_priority_columns'
down_revision = '2023_06_03_001'  # Point to the last known good migration
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to tasks table
    op.add_column('tasks', sa.Column('priority_source', sa.String(50), nullable=True, server_default='auto'))
    op.add_column('tasks', sa.Column('priority_score', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('tasks', sa.Column('priority_reasoning', postgresql.JSONB(), nullable=True, server_default='[]'))

    # Add check constraint for priority_source values
    op.create_check_constraint(
        'valid_priority_source',
        'tasks',
        "priority_source IN ('auto', 'manual', 'rule', 'ai')"
    )

def downgrade():
    # Remove the check constraint first
    op.drop_constraint('valid_priority_source', 'tasks')
    
    # Remove the columns
    op.drop_column('tasks', 'priority_reasoning')
    op.drop_column('tasks', 'priority_score')
    op.drop_column('tasks', 'priority_source') 