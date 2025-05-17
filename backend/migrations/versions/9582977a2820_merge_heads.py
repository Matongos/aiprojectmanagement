"""merge_heads

Revision ID: 9582977a2820
Revises: update_notifications_table
Create Date: 2025-05-17 21:16:59.423074

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9582977a2820'
down_revision: Union[str, None] = 'update_notifications_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
