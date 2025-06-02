"""merge ml models with existing migrations

Revision ID: bdf5d7827c18
Revises: add_user_expertise, merge_heads_005
Create Date: 2025-06-01 01:40:16.914038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bdf5d7827c18'
down_revision: Union[str, None] = ('add_user_expertise', 'merge_heads_005')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
