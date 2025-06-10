"""create task risks table fresh

Revision ID: create_task_risks_fresh
Revises: 
Create Date: 2024-03-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = 'create_task_risks_fresh'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create task_risks table
    op.create_table(
        'task_risks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('risk_level', sa.String(), nullable=False),
        sa.Column('time_sensitivity', sa.Float(), nullable=False),
        sa.Column('complexity', sa.Float(), nullable=False),
        sa.Column('priority', sa.Float(), nullable=False),
        sa.Column('risk_factors', JSON(), nullable=True),
        sa.Column('recommendations', JSON(), nullable=True),
        sa.Column('metrics', JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for faster lookups
    op.create_index(
        'ix_task_risks_task_id', 
        'task_risks', 
        ['task_id']
    )
    op.create_index(
        'ix_task_risks_created_at', 
        'task_risks', 
        ['created_at']
    )

def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_task_risks_created_at')
    op.drop_index('ix_task_risks_task_id')
    
    # Drop the table
    op.drop_table('task_risks') 