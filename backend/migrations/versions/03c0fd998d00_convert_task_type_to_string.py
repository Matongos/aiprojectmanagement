"""convert task_type to string

Revision ID: 03c0fd998d00
Revises: fix_task_type_string
Create Date: 2025-06-01 02:02:35.479106

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '03c0fd998d00'
down_revision: Union[str, None] = 'fix_task_type_string'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a temporary column of type string
    op.add_column('tasks', sa.Column('task_type_new', sa.String(50), nullable=True))
    
    # Copy data from the old enum column to the new string column
    op.execute("UPDATE tasks SET task_type_new = task_type::text")
    
    # Drop the old enum column
    op.drop_column('tasks', 'task_type')
    
    # Rename the new column to task_type
    op.alter_column('tasks', 'task_type_new', new_column_name='task_type')
    
    # Drop the enum type
    op.execute('DROP TYPE IF EXISTS tasktype')


def downgrade() -> None:
    # Create the enum type
    op.execute("CREATE TYPE tasktype AS ENUM ('DEVELOPMENT', 'DESIGN', 'TESTING', 'DOCUMENTATION', 'RESEARCH', 'PLANNING', 'REVIEW', 'BUG_FIX', 'MAINTENANCE', 'OTHER')")
    
    # Create a temporary column of type enum
    op.add_column('tasks', sa.Column('task_type_old', postgresql.ENUM('DEVELOPMENT', 'DESIGN', 'TESTING', 'DOCUMENTATION', 'RESEARCH', 'PLANNING', 'REVIEW', 'BUG_FIX', 'MAINTENANCE', 'OTHER', name='tasktype'), nullable=True))
    
    # Copy data from the string column to the enum column
    op.execute("UPDATE tasks SET task_type_old = task_type::tasktype")
    
    # Drop the string column
    op.drop_column('tasks', 'task_type')
    
    # Rename the enum column to task_type
    op.alter_column('tasks', 'task_type_old', new_column_name='task_type')
