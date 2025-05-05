"""Remove company_id from tasks table

This migration removes the unused company_id column from the tasks table.
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Drop the foreign key constraint first
    op.drop_constraint('tasks_company_id_fkey', 'tasks', type_='foreignkey')
    # Then drop the column
    op.drop_column('tasks', 'company_id')

def downgrade():
    # Add the column back
    op.add_column('tasks', sa.Column('company_id', sa.Integer(), nullable=True))
    # Add back the foreign key constraint
    op.create_foreign_key(
        'tasks_company_id_fkey',
        'tasks',
        'companies',
        ['company_id'],
        ['id']
    ) 