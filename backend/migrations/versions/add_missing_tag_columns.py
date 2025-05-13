"""add missing tag columns

Revision ID: 2024031901
Revises: 484b97e0165a
Create Date: 2024-03-19 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision: str = '2024031901'
down_revision: Union[str, None] = '484b97e0165a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to tags table."""
    # Add active column
    op.add_column('tags', sa.Column('active', sa.Boolean(), nullable=True, server_default='true'))
    
    # Add audit fields
    op.add_column('tags', sa.Column('create_uid', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('tags', sa.Column('create_date', sa.DateTime(timezone=True), server_default=func.now(), nullable=True))
    op.add_column('tags', sa.Column('write_uid', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('tags', sa.Column('write_date', sa.DateTime(timezone=True), onupdate=func.now(), nullable=True))
    
    # Update color column type from String(7) to Integer
    op.alter_column('tags', 'color',
                    existing_type=sa.String(length=7),
                    type_=sa.Integer(),
                    postgresql_using='1',  # Default to color index 1
                    existing_nullable=True)
    
    # Add unique constraint to name
    op.create_index(op.f('ix_tags_name'), 'tags', ['name'], unique=True)


def downgrade() -> None:
    """Remove added columns from tags table."""
    # Remove indexes
    op.drop_index(op.f('ix_tags_name'), table_name='tags')
    
    # Remove audit fields
    op.drop_column('tags', 'write_date')
    op.drop_column('tags', 'write_uid')
    op.drop_column('tags', 'create_date')
    op.drop_column('tags', 'create_uid')
    op.drop_column('tags', 'active')
    
    # Revert color column type
    op.alter_column('tags', 'color',
                    existing_type=sa.Integer(),
                    type_=sa.String(length=7),
                    postgresql_using='#3498db',  # Default to blue
                    existing_nullable=True) 