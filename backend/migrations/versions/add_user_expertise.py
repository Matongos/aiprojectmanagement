"""add user expertise fields

Revision ID: add_user_expertise
Revises: add_null_task_state
Create Date: 2024-03-14 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_user_expertise'
down_revision = 'add_null_task_state'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to users table
    op.add_column('users', sa.Column('profession', sa.String(), nullable=True))
    op.add_column('users', sa.Column('expertise', sa.ARRAY(sa.String()), nullable=True))
    op.add_column('users', sa.Column('skills', sa.ARRAY(sa.String()), nullable=True))
    op.add_column('users', sa.Column('experience_level', sa.String(), nullable=True))
    op.add_column('users', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('certifications', sa.ARRAY(sa.String()), nullable=True))
    op.add_column('users', sa.Column('preferred_working_hours', sa.String(), nullable=True))
    op.add_column('users', sa.Column('specializations', sa.ARRAY(sa.String()), nullable=True))
    
    # Initialize arrays as empty arrays instead of NULL
    op.execute("UPDATE users SET expertise = '{}' WHERE expertise IS NULL")
    op.execute("UPDATE users SET skills = '{}' WHERE skills IS NULL")
    op.execute("UPDATE users SET certifications = '{}' WHERE certifications IS NULL")
    op.execute("UPDATE users SET specializations = '{}' WHERE specializations IS NULL")

def downgrade():
    # Remove the new columns
    op.drop_column('users', 'specializations')
    op.drop_column('users', 'preferred_working_hours')
    op.drop_column('users', 'certifications')
    op.drop_column('users', 'notes')
    op.drop_column('users', 'experience_level')
    op.drop_column('users', 'skills')
    op.drop_column('users', 'expertise')
    op.drop_column('users', 'profession') 