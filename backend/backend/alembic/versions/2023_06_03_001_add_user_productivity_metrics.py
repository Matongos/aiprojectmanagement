"""add user productivity metrics table

Revision ID: 2023_06_03_001
Revises: 9616b3e0b6cd
Create Date: 2023-06-03 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2023_06_03_001'
down_revision = '9616b3e0b6cd'  # This should point to your latest migration
branch_labels = None
depends_on = None

def upgrade():
    # Create user_productivity_metrics table
    op.create_table(
        'user_productivity_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('productivity_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('completed_tasks', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_time_spent', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('avg_complexity', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('task_breakdown', postgresql.JSONB(), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('analysis_period_days', sa.Integer(), nullable=True, server_default='30'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on user_id for faster lookups
    op.create_index(
        op.f('ix_user_productivity_metrics_user_id'),
        'user_productivity_metrics',
        ['user_id'],
        unique=False
    )

def downgrade():
    # Drop index first
    op.drop_index(op.f('ix_user_productivity_metrics_user_id'), table_name='user_productivity_metrics')
    # Then drop the table
    op.drop_table('user_productivity_metrics') 