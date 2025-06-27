"""final merge heads

Revision ID: 04458db79910
Revises: 0c42dd3bf457, 59e050c74e74
Create Date: 2025-06-27 16:02:05.754480

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04458db79910'
down_revision: Union[str, None] = ('0c42dd3bf457', '59e050c74e74')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
