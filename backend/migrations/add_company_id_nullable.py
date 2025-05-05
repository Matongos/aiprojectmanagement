"""Add company_id back to tasks table as nullable

This migration adds back the company_id column to the tasks table, but makes it nullable.
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add the column
    op.add_column('tasks', sa.Column('company_id', sa.Integer(), nullable=True))
    # Add the foreign key constraint
    op.create_foreign_key(
        'tasks_company_id_fkey',
        'tasks',
        'companies',
        ['company_id'],
        ['id']
    )

def downgrade():
    # Drop the foreign key constraint first
    op.drop_constraint('tasks_company_id_fkey', 'tasks', type_='foreignkey')
    # Then drop the column
    op.drop_column('tasks', 'company_id') 