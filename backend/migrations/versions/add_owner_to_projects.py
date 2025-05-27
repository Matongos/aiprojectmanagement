"""add owner_id to projects

Revision ID: add_owner_to_projects
Revises: add_metrics_tables_006
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_owner_to_projects'
down_revision = 'add_metrics_tables_006'
branch_labels = None
depends_on = None

def upgrade():
    # Add owner_id column to projects table
    op.add_column('projects', sa.Column('owner_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_project_owner',
        'projects', 'users',
        ['owner_id'], ['id'],
        ondelete='SET NULL'
    )

def downgrade():
    # Remove owner_id column from projects table
    op.drop_constraint('fk_project_owner', 'projects', type_='foreignkey')
    op.drop_column('projects', 'owner_id') 