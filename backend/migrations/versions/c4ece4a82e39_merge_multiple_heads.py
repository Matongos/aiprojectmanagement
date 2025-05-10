"""merge_multiple_heads

Revision ID: c4ece4a82e39
Revises: add_company_id_to_tasks_2, add_is_active_to_milestones, add_parent_id_comments
Create Date: 2025-05-10 15:19:15.168274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4ece4a82e39'
down_revision: Union[str, None] = ('add_company_id_to_tasks_2', 'add_is_active_to_milestones', 'add_parent_id_comments')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
