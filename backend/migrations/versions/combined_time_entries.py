"""combined time entries

Revision ID: combined_time_entries_001
Revises: None
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic
revision = 'combined_time_entries_001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Check if table exists
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    
    if 'time_entries' not in tables:
        op.create_table('time_entries',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('duration', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('activity_type', sa.String(length=50), nullable=True),
            sa.Column('is_billable', sa.Boolean(), nullable=True, server_default='true'),
            sa.Column('is_running', sa.Boolean(), nullable=True, server_default='false'),
            sa.Column('task_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=True),
            sa.Column('productivity_score', sa.Float(), nullable=True),
            sa.Column('efficiency_metrics', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
            sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

def downgrade():
    op.drop_table('time_entries') 