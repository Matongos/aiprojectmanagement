"""merge heads

Revision ID: 9616b3e0b6cd
Revises: 87e1d99f7ce9
Create Date: 2025-04-30 02:09:42.218820

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9616b3e0b6cd'
down_revision: Union[str, None] = '87e1d99f7ce9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
