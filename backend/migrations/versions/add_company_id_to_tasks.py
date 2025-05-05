"""add company_id to tasks

Revision ID: add_company_id_to_tasks
Revises: 9eb578cefdeb
Create Date: 2024-03-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_company_id_to_tasks_2'
down_revision: Union[str, None] = '9eb578cefdeb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add company_id column to tasks table
    op.add_column('tasks', sa.Column('company_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_tasks_company_id_companies',
        'tasks', 'companies',
        ['company_id'], ['id']
    )


def downgrade() -> None:
    # Remove company_id column from tasks table
    op.drop_constraint('fk_tasks_company_id_companies', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'company_id') 