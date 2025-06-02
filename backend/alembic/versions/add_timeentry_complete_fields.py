"""add complete timeentry fields

Revision ID: add_timeentry_complete_fields
Revises: add_sample_success_patterns
Create Date: 2024-03-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_timeentry_complete_fields'
down_revision = 'add_sample_success_patterns'  # This should point to your last successful migration
branch_labels = None
depends_on = None

def upgrade():
    # Add all necessary columns to time_entries table
    
    # Add time tracking columns
    op.add_column('time_entries', sa.Column('start_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('time_entries', sa.Column('end_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('time_entries', sa.Column('entry_date', sa.Date(), server_default=sa.func.current_date(), nullable=False))
    
    # Add analytics fields
    op.add_column('time_entries', sa.Column('productivity_score', sa.Float(), nullable=True))
    op.add_column('time_entries', sa.Column('efficiency_metrics', postgresql.JSONB(), nullable=True))
    
    # Create indexes for better query performance
    op.create_index(op.f('ix_time_entries_start_time'), 'time_entries', ['start_time'], unique=False)
    op.create_index(op.f('ix_time_entries_end_time'), 'time_entries', ['end_time'], unique=False)
    op.create_index(op.f('ix_time_entries_entry_date'), 'time_entries', ['entry_date'], unique=False)

def downgrade():
    # Remove all added columns from time_entries table
    op.drop_index(op.f('ix_time_entries_entry_date'), table_name='time_entries')
    op.drop_index(op.f('ix_time_entries_end_time'), table_name='time_entries')
    op.drop_index(op.f('ix_time_entries_start_time'), table_name='time_entries')
    
    op.drop_column('time_entries', 'efficiency_metrics')
    op.drop_column('time_entries', 'productivity_score')
    op.drop_column('time_entries', 'entry_date')
    op.drop_column('time_entries', 'end_time')
    op.drop_column('time_entries', 'start_time') 