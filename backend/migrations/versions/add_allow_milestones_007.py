"""add allow_milestones to projects

Revision ID: add_allow_milestones_007
Create Date: 2024-03-20 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'add_allow_milestones_007'
down_revision = 'add_metrics_tables_006'  # This should point to the previous migration
branch_labels = None
depends_on = None

def upgrade():
    # Add allow_milestones column to projects table
    op.add_column('projects',
        sa.Column('allow_milestones', sa.Boolean(), nullable=False, server_default='true')
    )

def downgrade():
    # Remove allow_milestones column from projects table
    op.drop_column('projects', 'allow_milestones') 