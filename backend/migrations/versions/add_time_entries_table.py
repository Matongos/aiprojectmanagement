"""add time entries table

Revision ID: add_time_entries_001
Revises: add_metrics_tables_006
Create Date: 2024-05-27 01:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_time_entries_001'
down_revision = 'add_metrics_tables_006'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'time_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration', sa.Float(), nullable=False),
        sa.Column('is_running', sa.Boolean(), default=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('activity_type', sa.String(50), nullable=True),
        sa.Column('is_billable', sa.Boolean(), default=True),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('productivity_score', sa.Float(), nullable=True),
        sa.Column('efficiency_metrics', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(
        'ix_time_entries_task_id',
        'time_entries',
        ['task_id']
    )
    op.create_index(
        'ix_time_entries_user_id',
        'time_entries',
        ['user_id']
    )
    op.create_index(
        'ix_time_entries_project_id',
        'time_entries',
        ['project_id']
    )
    op.create_index(
        'ix_time_entries_start_time',
        'time_entries',
        ['start_time']
    )

def downgrade():
    op.drop_index('ix_time_entries_start_time')
    op.drop_index('ix_time_entries_project_id')
    op.drop_index('ix_time_entries_user_id')
    op.drop_index('ix_time_entries_task_id')
    op.drop_table('time_entries') 