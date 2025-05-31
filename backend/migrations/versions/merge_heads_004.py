"""merge heads

Revision ID: merge_heads_004
Revises: convert_role_to_integer_009, merge_task_migrations_013
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'merge_heads_004'
down_revision = None
branch_labels = None
depends_on = ['convert_role_to_integer_009', 'merge_task_migrations_013']

def upgrade():
    pass

def downgrade():
    pass 