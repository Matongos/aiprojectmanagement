"""create project followers table

Revision ID: create_project_followers_table
Revises: add_task_followers_table
Create Date: 2024-03-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'create_project_followers_table'
down_revision: Union[str, None] = 'add_task_followers_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create project_followers table."""
    op.create_table(
        'project_followers',
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('project_id', 'user_id')
    )
    op.create_index(op.f('ix_project_followers_project_id'), 'project_followers', ['project_id'], unique=False)
    op.create_index(op.f('ix_project_followers_user_id'), 'project_followers', ['user_id'], unique=False)


def downgrade() -> None:
    """Drop project_followers table."""
    op.drop_index(op.f('ix_project_followers_user_id'), table_name='project_followers')
    op.drop_index(op.f('ix_project_followers_project_id'), table_name='project_followers')
    op.drop_table('project_followers') 