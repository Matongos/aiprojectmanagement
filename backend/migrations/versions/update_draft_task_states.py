"""update draft task states

Revision ID: update_draft_task_states
Revises: c4ece4a82e39
Create Date: 2024-03-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'update_draft_task_states'
down_revision: Union[str, None] = 'c4ece4a82e39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update all tasks with state='draft' to state='in_progress'
    op.execute("UPDATE tasks SET state = 'in_progress' WHERE state = 'draft'")


def downgrade() -> None:
    # We don't want to revert back to draft state
    pass 