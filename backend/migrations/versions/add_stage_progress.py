"""add progress field to project_stages

Revision ID: add_stage_progress
Revises: 58131ff61436
Create Date: 2024-03-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_stage_progress'
down_revision = '58131ff61436'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add progress column to project_stages
    op.add_column('project_stages',
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    # Remove progress column from project_stages
    op.drop_column('project_stages', 'progress') 