"""Create ml_models table

Revision ID: create_ml_models_table
Revises: 03c0fd998d00
Create Date: 2025-06-01 02:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_ml_models_table'
down_revision: Union[str, None] = '03c0fd998d00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ml_models table
    op.create_table(
        'ml_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('model_type', sa.String(), nullable=True),
        sa.Column('model_version', sa.String(), nullable=True),
        sa.Column('performance_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('hyperparameters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('feature_importance', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_trained', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on id
    op.create_index('ix_ml_models_id', 'ml_models', ['id'], unique=False)
    
    # Insert default completion time predictor model
    op.execute("""
        INSERT INTO ml_models (
            model_name,
            model_type,
            model_version,
            performance_metrics,
            hyperparameters,
            is_active
        ) VALUES (
            'Task Completion Time Predictor',
            'completion_time_predictor',
            '1.0.0',
            '{"mae": 0.5, "rmse": 0.7, "r2": 0.8}'::json,
            '{"n_estimators": 100, "max_depth": 10}'::json,
            true
        )
    """)


def downgrade() -> None:
    # Drop the table and its index
    op.drop_index('ix_ml_models_id', table_name='ml_models')
    op.drop_table('ml_models') 