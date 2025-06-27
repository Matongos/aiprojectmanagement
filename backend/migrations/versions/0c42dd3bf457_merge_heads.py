"""merge heads

Revision ID: 0c42dd3bf457
Revises: add_task_complexity_fields
Create Date: 2025-06-27 16:01:27.359894

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c42dd3bf457'
down_revision: Union[str, None] = 'add_task_complexity_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
