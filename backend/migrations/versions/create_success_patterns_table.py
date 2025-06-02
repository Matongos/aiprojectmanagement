"""create success patterns table

Revision ID: create_success_patterns_table
Revises: 7e86c1f8e90e
Create Date: 2025-06-01 02:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_success_patterns_table'
down_revision: Union[str, None] = '7e86c1f8e90e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create success_patterns table
    op.create_table(
        'success_patterns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pattern_type', sa.String(), nullable=True),
        sa.Column('pattern_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), nullable=True),
        sa.Column('impact_score', sa.Float(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), onupdate=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on id
    op.create_index('ix_success_patterns_id', 'success_patterns', ['id'], unique=False)


def downgrade() -> None:
    # Drop success_patterns table
    op.drop_index('ix_success_patterns_id', table_name='success_patterns')
    op.drop_table('success_patterns') 