"""add task_tag table

Revision ID: 2024032001
Revises: add_company_id_to_tasks_2
Create Date: 2024-03-20 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2024032001'
down_revision: Union[str, None] = 'add_company_id_to_tasks_2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create task_tag table."""
    # Create task_tag association table
    op.create_table(
        'task_tag',
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('task_id', 'tag_id')
    )


def downgrade() -> None:
    """Remove task_tag table."""
    op.drop_table('task_tag') 