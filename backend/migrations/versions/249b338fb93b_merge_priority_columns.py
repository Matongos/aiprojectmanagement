"""merge_priority_columns

Revision ID: 249b338fb93b
Revises: add_sample_success_patterns, add_task_priority_columns
Create Date: 2025-06-05 04:38:19.814590

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '249b338fb93b'
down_revision: Union[str, None] = ('add_sample_success_patterns', 'add_task_priority_columns')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
