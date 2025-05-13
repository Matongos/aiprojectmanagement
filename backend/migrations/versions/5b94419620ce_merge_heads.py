"""merge heads

Revision ID: 5b94419620ce
Revises: 88d63db0cf68, 2024032001
Create Date: 2025-05-13 05:01:59.469282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b94419620ce'
down_revision: Union[str, None] = ('88d63db0cf68', '2024032001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
