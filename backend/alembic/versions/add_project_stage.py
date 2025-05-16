"""add project stage

Revision ID: add_project_stage
Revises: 
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_project_stage'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create enum type for project stages
    op.execute("CREATE TYPE project_stage AS ENUM ('to_do', 'in_progress', 'done', 'cancelled')")
    
    # Add stage column to projects table
    op.add_column('projects', sa.Column('stage', sa.Enum('to_do', 'in_progress', 'done', 'cancelled', name='project_stage'), nullable=True))

def downgrade():
    # Remove stage column
    op.drop_column('projects', 'stage')
    
    # Drop enum type
    op.execute("DROP TYPE project_stage") 