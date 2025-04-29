"""merge multiple heads

Revision ID: 75dc050f2cec
Revises: 6293461dc52a, add_file_attachments, add_stage_progress, 2023_add_email_notifications
Create Date: 2025-04-28 16:54:48.532510

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75dc050f2cec'
down_revision: Union[str, None] = ('6293461dc52a', 'add_file_attachments', 'add_stage_progress', '2023_add_email_notifications')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
