"""Fix task priority columns

Revision ID: fix_task_priority_columns
Revises: 2023_06_03_001
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = 'fix_task_priority_columns'
down_revision = '2023_06_03_001'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to tasks table if they don't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('tasks')]
    
    if 'priority_source' not in existing_columns:
        op.add_column('tasks', sa.Column('priority_source', sa.String(50), nullable=True, server_default='auto'))
    
    if 'priority_score' not in existing_columns:
        op.add_column('tasks', sa.Column('priority_score', sa.Float(), nullable=True, server_default='0.0'))
    
    if 'priority_reasoning' not in existing_columns:
        op.add_column('tasks', sa.Column('priority_reasoning', postgresql.JSONB(), nullable=True, server_default='[]'))

    # Add check constraint if it doesn't exist
    try:
        op.create_check_constraint(
            'valid_priority_source',
            'tasks',
            "priority_source IN ('auto', 'manual', 'rule', 'ai')"
        )
    except Exception:
        pass  # Constraint might already exist

def downgrade():
    # Remove the check constraint first
    try:
        op.drop_constraint('valid_priority_source', 'tasks')
    except Exception:
        pass  # Constraint might not exist
    
    # Remove the columns
    op.drop_column('tasks', 'priority_reasoning')
    op.drop_column('tasks', 'priority_score')
    op.drop_column('tasks', 'priority_source') 