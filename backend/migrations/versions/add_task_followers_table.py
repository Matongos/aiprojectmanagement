"""add task followers table

Revision ID: add_task_followers_table
Revises: add_messages_table
Create Date: 2024-03-22 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_task_followers_table'
down_revision: Union[str, None] = 'add_messages_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create task_followers table."""
    op.create_table(
        'task_followers',
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('task_id', 'user_id')
    )
    op.create_index(op.f('ix_task_followers_task_id'), 'task_followers', ['task_id'], unique=False)
    op.create_index(op.f('ix_task_followers_user_id'), 'task_followers', ['user_id'], unique=False)


def downgrade() -> None:
    """Drop task_followers table."""
    op.drop_index(op.f('ix_task_followers_user_id'), table_name='task_followers')
    op.drop_index(op.f('ix_task_followers_task_id'), table_name='task_followers')
    op.drop_table('task_followers') 