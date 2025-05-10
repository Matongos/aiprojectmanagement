"""add_is_active_to_milestones

Revision ID: add_is_active_to_milestones
Revises: 6dbe281680a6
Create Date: 2024-03-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_is_active_to_milestones'
down_revision: Union[str, None] = '6dbe281680a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Add is_active column to milestones table."""
    op.add_column('milestones', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

def downgrade() -> None:
    """Remove is_active column from milestones table."""
    op.drop_column('milestones', 'is_active') 