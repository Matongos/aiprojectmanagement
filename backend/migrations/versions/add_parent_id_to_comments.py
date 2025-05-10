"""add parent_id to comments

Revision ID: add_parent_id_comments
Revises: 6dbe281680a6
Create Date: 2024-03-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_parent_id_comments'
down_revision: Union[str, None] = '6dbe281680a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add parent_id column to comments table if it doesn't exist
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'comments' 
            AND column_name = 'parent_id'
        ) THEN
            ALTER TABLE comments 
            ADD COLUMN parent_id INTEGER REFERENCES comments(id) ON DELETE CASCADE;
        END IF;
    END
    $$;
    """)

def downgrade() -> None:
    # Remove parent_id column from comments table if it exists
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'comments' 
            AND column_name = 'parent_id'
        ) THEN
            ALTER TABLE comments 
            DROP COLUMN parent_id;
        END IF;
    END
    $$;
    """) 