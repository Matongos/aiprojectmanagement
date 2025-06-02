"""Fix task_type to use String instead of Enum

Revision ID: fix_task_type_string
Revises: bc57083510ff
Create Date: 2025-06-01 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fix_task_type_string'
down_revision: Union[str, None] = 'bc57083510ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing task_type column and its enum type
    op.drop_column('tasks', 'task_type')
    op.execute('DROP TYPE IF EXISTS tasktype')
    
    # Add the new task_type column as String(50)
    op.add_column('tasks', sa.Column('task_type', sa.String(50), nullable=True))


def downgrade() -> None:
    # Create the enum type
    op.execute("CREATE TYPE tasktype AS ENUM ('DEVELOPMENT', 'DESIGN', 'TESTING', 'DOCUMENTATION', 'RESEARCH', 'PLANNING', 'REVIEW', 'BUG_FIX', 'MAINTENANCE', 'OTHER')")
    
    # Drop the string column and add back the enum column
    op.drop_column('tasks', 'task_type')
    op.add_column('tasks', sa.Column('task_type', sa.Enum('DEVELOPMENT', 'DESIGN', 'TESTING', 'DOCUMENTATION', 'RESEARCH', 'PLANNING', 'REVIEW', 'BUG_FIX', 'MAINTENANCE', 'OTHER', name='tasktype'), nullable=True)) 