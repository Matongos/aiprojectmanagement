"""merge multiple heads

Revision ID: merge_heads_003
Revises: add_project_role_enum_008, 89f67b23310c
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'merge_heads_003'
down_revision = None
branch_labels = None
depends_on = ('add_project_role_enum_008', '89f67b23310c')

def upgrade():
    pass

def downgrade():
    pass 