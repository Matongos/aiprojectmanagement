"""add project role enum

Revision ID: add_project_role_enum_008
Revises: add_allow_milestones_007
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'add_project_role_enum_008'
down_revision = 'add_allow_milestones_007'  # Point to the previous migration
branch_labels = None
depends_on = None

def upgrade():
    # Drop existing enum type if exists
    op.execute("DROP TYPE IF EXISTS projectrole")
    
    # Create role column as integer with check constraint
    op.add_column('project_members', sa.Column('new_role', 
        sa.Integer,
        sa.CheckConstraint('new_role IN (1, 2, 3)'),  # 1=manager, 2=member, 3=viewer
        nullable=True
    ))
    
    # Convert existing roles to numeric values
    op.execute("""
        UPDATE project_members 
        SET new_role = CASE 
            WHEN role = 'manager' THEN 1
            WHEN role = 'member' THEN 2
            ELSE 3
        END
    """)
    
    # Drop the old role column and rename the new one
    op.drop_column('project_members', 'role')
    op.alter_column('project_members', 'new_role', 
        new_column_name='role',
        nullable=False,
        server_default=sa.text("2")  # Default to MEMBER (2)
    )

def downgrade():
    # Add a temporary column for the string values
    op.add_column('project_members', sa.Column('role_str', sa.String, nullable=True))
    
    # Convert integer values to strings
    op.execute("""
        UPDATE project_members 
        SET role_str = CASE 
            WHEN role = 1 THEN 'manager'
            WHEN role = 2 THEN 'member'
            ELSE 'viewer'
        END
    """)
    
    # Drop the integer role column
    op.drop_column('project_members', 'role')
    
    # Rename the string column to role
    op.alter_column('project_members', 'role_str',
        new_column_name='role',
        nullable=False,
        server_default=sa.text("'member'")
    ) 