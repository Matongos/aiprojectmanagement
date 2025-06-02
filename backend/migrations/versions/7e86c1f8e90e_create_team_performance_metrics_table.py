"""create team performance metrics table

Revision ID: 7e86c1f8e90e
Revises: create_ml_models_table
Create Date: 2025-06-01 02:18:17.104209

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7e86c1f8e90e'
down_revision: Union[str, None] = 'create_ml_models_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create team_performance_metrics table
    op.create_table(
        'team_performance_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('time_period', sa.String(), nullable=True),
        sa.Column('velocity', sa.Float(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('collaboration_score', sa.Float(), nullable=True),
        sa.Column('efficiency_score', sa.Float(), nullable=True),
        sa.Column('metrics_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_team_performance_metrics_id', 'team_performance_metrics', ['id'], unique=False)


def downgrade() -> None:
    # Drop team_performance_metrics table
    op.drop_index('ix_team_performance_metrics_id', table_name='team_performance_metrics')
    op.drop_table('team_performance_metrics')
