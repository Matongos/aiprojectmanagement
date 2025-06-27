"""merge heads

Revision ID: 59e050c74e74
Revises: add_productivity_history
Create Date: 2025-06-27 16:01:40.960770

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59e050c74e74'
down_revision: Union[str, None] = 'add_productivity_history'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
