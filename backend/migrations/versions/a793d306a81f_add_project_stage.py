"""add project stage

Revision ID: a793d306a81f
Revises: 7aec3e517ef1
Create Date: 2024-03-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a793d306a81f'
down_revision: Union[str, None] = '7aec3e517ef1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add project stage enum and column."""
    # Create enum type for project stages
    op.execute("CREATE TYPE project_stage AS ENUM ('to_do', 'in_progress', 'done', 'cancelled')")
    
    # Add stage column to projects table
    op.add_column('projects', sa.Column('stage', sa.Enum('to_do', 'in_progress', 'done', 'cancelled', name='project_stage'), nullable=True))


def downgrade() -> None:
    """Remove project stage column and enum."""
    # Drop stage column
    op.drop_column('projects', 'stage')
    
    # Drop enum type
    op.execute("DROP TYPE project_stage")
