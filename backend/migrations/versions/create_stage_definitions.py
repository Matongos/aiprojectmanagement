"""create stage definitions

Revision ID: create_stage_definitions
Revises: a793d306a81f
Create Date: 2024-03-21
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_stage_definitions'
down_revision = 'a793d306a81f'
branch_labels = None
depends_on = None

def upgrade():
    # Create stage definitions table
    op.create_table(
        'stage_definitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Insert default stage definitions
    op.execute("""
        INSERT INTO stage_definitions (id, name, description) VALUES 
        (1, 'to_do', 'Tasks that need to be started'),
        (2, 'in_progress', 'Tasks currently being worked on'),
        (3, 'done', 'Completed tasks'),
        (4, 'cancelled', 'Cancelled or abandoned tasks')
    """)

    # Drop the old stage column if it exists
    op.drop_column('projects', 'stage')

    # Add new stage column referencing stage_definitions
    op.add_column('projects', sa.Column('stage_id', sa.Integer(), sa.ForeignKey('stage_definitions.id'), nullable=True))

def downgrade():
    # Drop new stage column
    op.drop_column('projects', 'stage_id')
    
    # Drop stage definitions table
    op.drop_table('stage_definitions') 