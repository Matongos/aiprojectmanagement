"""add parent_id to comments

Revision ID: 6dbe281680a6
Revises: 484b97e0165a
Create Date: 2024-03-19 12:34:56.789012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6dbe281680a6'
down_revision: Union[str, None] = '484b97e0165a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add parent_id column to comments table
    op.add_column('comments', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_comments_parent_id',
        'comments', 'comments',
        ['parent_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Remove parent_id column from comments table
    op.drop_constraint('fk_comments_parent_id', 'comments', type_='foreignkey')
    op.drop_column('comments', 'parent_id')
