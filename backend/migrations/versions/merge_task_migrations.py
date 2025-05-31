"""merge task migrations

Revision ID: merge_task_migrations_013
Revises: convert_role_to_integer_009
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'merge_task_migrations_013'
down_revision = 'convert_role_to_integer_009'
branch_labels = None
depends_on = None

def upgrade():
    # First ensure the enum type exists
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'completionstatus') THEN
                CREATE TYPE completionstatus AS ENUM ('NOT_COMPLETED', 'COMPLETED', 'CANCELLED');
            END IF;
        END$$;
    """)

    # Add columns if they don't exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                         WHERE table_name = 'tasks' AND column_name = 'is_active') THEN
                ALTER TABLE tasks ADD COLUMN is_active boolean NOT NULL DEFAULT true;
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                         WHERE table_name = 'tasks' AND column_name = 'completion_status') THEN
                ALTER TABLE tasks ADD COLUMN completion_status completionstatus NOT NULL DEFAULT 'NOT_COMPLETED';
            END IF;
        END$$;
    """)

    # Update existing tasks with default values
    op.execute("""
        UPDATE tasks 
        SET is_active = CASE 
            WHEN state IN ('done', 'canceled') THEN false 
            ELSE true 
        END,
        completion_status = CASE 
            WHEN state = 'done' THEN 'COMPLETED'::completionstatus
            WHEN state = 'canceled' THEN 'CANCELLED'::completionstatus
            ELSE 'NOT_COMPLETED'::completionstatus
        END
        WHERE is_active IS NULL OR completion_status IS NULL;
    """)

def downgrade():
    # Drop the columns if they exist
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                     WHERE table_name = 'tasks' AND column_name = 'completion_status') THEN
                ALTER TABLE tasks DROP COLUMN completion_status;
            END IF;
            
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                     WHERE table_name = 'tasks' AND column_name = 'is_active') THEN
                ALTER TABLE tasks DROP COLUMN is_active;
            END IF;
        END$$;
    """)

    # Drop the enum type if it exists
    op.execute("DROP TYPE IF EXISTS completionstatus CASCADE;") 