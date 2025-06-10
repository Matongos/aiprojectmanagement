"""add task risk table

Revision ID: add_task_risk_table
Revises: add_timeentry_complete_fields
Create Date: 2024-03-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = 'add_task_risk_table'
down_revision = 'add_timeentry_complete_fields'  # Points to the previous migration
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