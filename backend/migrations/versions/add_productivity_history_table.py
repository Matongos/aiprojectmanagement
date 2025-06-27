"""add user productivity history table

Revision ID: add_productivity_history
Revises: 51f4d66c2b48
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_productivity_history'
down_revision = '51f4d66c2b48'
branch_labels = None
depends_on = None

def upgrade():
    # Create user_productivity_history table
    op.create_table(
        'user_productivity_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('productivity_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('completed_tasks', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_time_spent', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('avg_complexity', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('tasks_started', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('tasks_in_progress', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('completion_rate', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('avg_completion_time', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('score_trend', sa.String(20), nullable=True, server_default='stable'),
        sa.Column('trend_percentage', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for faster lookups
    op.create_index(
        op.f('ix_user_productivity_history_user_id'),
        'user_productivity_history',
        ['user_id'],
        unique=False
    )
    
    op.create_index(
        op.f('ix_user_productivity_history_snapshot_date'),
        'user_productivity_history',
        ['snapshot_date'],
        unique=False
    )
    
    op.create_index(
        op.f('ix_user_productivity_history_period_type'),
        'user_productivity_history',
        ['period_type'],
        unique=False
    )
    
    # Create unique constraint to prevent duplicate snapshots
    op.create_unique_constraint(
        'uq_user_productivity_history_user_date_period',
        'user_productivity_history',
        ['user_id', 'snapshot_date', 'period_type']
    )

def downgrade():
    # Drop indexes and constraints
    op.drop_constraint('uq_user_productivity_history_user_date_period', 'user_productivity_history', type_='unique')
    op.drop_index(op.f('ix_user_productivity_history_period_type'), table_name='user_productivity_history')
    op.drop_index(op.f('ix_user_productivity_history_snapshot_date'), table_name='user_productivity_history')
    op.drop_index(op.f('ix_user_productivity_history_user_id'), table_name='user_productivity_history')
    
    # Drop table
    op.drop_table('user_productivity_history') 