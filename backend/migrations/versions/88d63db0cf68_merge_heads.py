"""merge heads

Revision ID: 88d63db0cf68
Revises: 2024031901, update_draft_task_states
Create Date: 2025-05-13 04:32:19.574954

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88d63db0cf68'
down_revision: Union[str, None] = ('2024031901', 'update_draft_task_states')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
