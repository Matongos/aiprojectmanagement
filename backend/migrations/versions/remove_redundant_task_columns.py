"""remove redundant task columns

Revision ID: remove_redundant_task_columns
Revises: merge_task_migrations
Create Date: 2024-03-30 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'remove_redundant_task_columns'
down_revision = 'merge_task_migrations'
branch_labels = None
depends_on = None

def upgrade():
    # Remove redundant columns
    op.drop_column('tasks', 'is_active')
    op.drop_column('tasks', 'completion_status')

def downgrade():
    # Add back the columns if needed to rollback
    op.add_column('tasks', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('tasks', sa.Column('completion_status', 
        postgresql.ENUM('NOT_COMPLETED', 'COMPLETED', 'CANCELLED', name='completionstatus'),
        nullable=False, 
        server_default='NOT_COMPLETED'
    )) 