"""empty message

Revision ID: 580a5bea3952
Revises: add_null_task_state, base
Create Date: 2025-05-31 12:36:11.877810

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '580a5bea3952'
down_revision: Union[str, None] = ('add_null_task_state', 'base')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
