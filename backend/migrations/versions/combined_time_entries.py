"""combined time entries table

Revision ID: combined_time_entries_001
Revises: 
Create Date: 2024-05-28 00:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'combined_time_entries_001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('time_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('duration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('activity_type', sa.String(50), nullable=True),
        sa.Column('is_billable', sa.Boolean(), server_default='true'),
        sa.Column('is_running', sa.Boolean(), server_default='false'),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('productivity_score', sa.Float(), nullable=True),
        sa.Column('efficiency_metrics', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_time_entries_id'), 'time_entries', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_time_entries_id'), table_name='time_entries')
    op.drop_table('time_entries') 