"""Add project urgency score

Revision ID: add_project_urgency_score
Revises: 249b338fb93b
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'add_project_urgency_score'
down_revision = '249b338fb93b'  # Point to the merge migration
branch_labels = None
depends_on = None

def upgrade():
    # Add urgency_score column to projects table
    op.add_column('projects', sa.Column('urgency_score', sa.Float(), nullable=True, server_default='0.5'))

def downgrade():
    # Remove the column
    op.drop_column('projects', 'urgency_score') 