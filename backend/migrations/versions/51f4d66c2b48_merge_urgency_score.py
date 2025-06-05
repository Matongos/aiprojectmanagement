"""merge_urgency_score

Revision ID: 51f4d66c2b48
Revises: add_project_urgency_score, fix_task_priority_columns
Create Date: 2025-06-05 04:48:34.249216

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51f4d66c2b48'
down_revision: Union[str, None] = ('add_project_urgency_score', 'fix_task_priority_columns')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
