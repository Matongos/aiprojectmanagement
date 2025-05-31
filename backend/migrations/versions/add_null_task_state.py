"""add null task state

Revision ID: add_null_task_state
Revises: 
Create Date: 2024-03-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_null_task_state'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Drop existing check constraint
    op.execute('ALTER TABLE tasks DROP CONSTRAINT IF EXISTS valid_task_states')
    
    # Add new check constraint including 'null' state
    op.create_check_constraint(
        'valid_task_states',
        'tasks',
        "state IN ('null', 'in_progress', 'changes_requested', 'approved', 'canceled', 'done')"
    )
    
    # Update existing tasks with NULL state if they don't have a state
    op.execute("UPDATE tasks SET state = 'null' WHERE state IS NULL")

def downgrade():
    # Drop new check constraint
    op.execute('ALTER TABLE tasks DROP CONSTRAINT IF EXISTS valid_task_states')
    
    # Add old check constraint back
    op.create_check_constraint(
        'valid_task_states',
        'tasks',
        "state IN ('in_progress', 'changes_requested', 'approved', 'canceled', 'done')"
    )
    
    # Update NULL states to IN_PROGRESS
    op.execute("UPDATE tasks SET state = 'in_progress' WHERE state = 'null'") 