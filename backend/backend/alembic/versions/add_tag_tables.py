"""add tag tables

Revision ID: 2023a1b3c4d5
Revises: 9616b3e0b6cd
Create Date: 2024-03-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision: str = '2023a1b3c4d5'
down_revision: Union[str, None] = '9616b3e0b6cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tag-related tables."""
    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('color', sa.Integer(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('create_uid', sa.Integer(), nullable=True),
        sa.Column('create_date', sa.DateTime(timezone=True), server_default=func.now()),
        sa.Column('write_uid', sa.Integer(), nullable=True),
        sa.Column('write_date', sa.DateTime(timezone=True), onupdate=func.now()),
        sa.ForeignKeyConstraint(['create_uid'], ['users.id'], ),
        sa.ForeignKeyConstraint(['write_uid'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tags_id'), 'tags', ['id'], unique=False)
    op.create_index(op.f('ix_tags_name'), 'tags', ['name'], unique=True)

    # Create project_tag association table
    op.create_table(
        'project_tag',
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('project_id', 'tag_id')
    )

    # Create task_tag association table
    op.create_table(
        'task_tag',
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('task_id', 'tag_id')
    )


def downgrade() -> None:
    """Remove tag-related tables."""
    # Drop tables in reverse order of creation
    op.drop_table('task_tag')
    op.drop_table('project_tag')
    op.drop_index(op.f('ix_tags_name'), table_name='tags')
    op.drop_index(op.f('ix_tags_id'), table_name='tags')
    op.drop_table('tags') 