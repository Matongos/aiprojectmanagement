"""merge heads for task risk

Revision ID: merge_heads_task_risk
Revises: add_project_stage, add_task_risk_table
Create Date: 2024-03-10 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads_task_risk'
down_revision = None
branch_labels = None
depends_on = ('add_project_stage', 'add_task_risk_table')

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass 