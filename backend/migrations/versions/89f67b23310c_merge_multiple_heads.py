"""merge multiple heads

Revision ID: 89f67b23310c
Revises: add_owner_to_projects, add_pgvector_001, merge_heads_001
Create Date: 2025-05-27 06:21:44.091104

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89f67b23310c'
down_revision: Union[str, None] = ('add_owner_to_projects', 'add_pgvector_001', 'merge_heads_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
