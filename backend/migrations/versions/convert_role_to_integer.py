"""convert role to integer

Revision ID: convert_role_to_integer_009
Revises: merge_heads_003
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'convert_role_to_integer_009'
down_revision = 'merge_heads_003'
branch_labels = None
depends_on = None

def upgrade():
    # Create a new integer column
    op.add_column('project_members', sa.Column('role_int', 
        sa.Integer,
        sa.CheckConstraint('role_int IN (1, 2, 3)'),  # 1=manager, 2=member, 3=viewer
        nullable=True
    ))
    
    # Convert existing string values to integers
    op.execute("""
        UPDATE project_members 
        SET role_int = CASE 
            WHEN role::text = 'manager' THEN 1
            WHEN role::text = 'member' THEN 2
            ELSE 3
        END
    """)
    
    # Drop the old role column and rename the new one
    op.drop_column('project_members', 'role')
    op.alter_column('project_members', 'role_int', 
        new_column_name='role',
        nullable=False,
        server_default=sa.text("2")  # Default to MEMBER (2)
    )

def downgrade():
    # Create a new string column
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
    
    # Drop the integer column and rename the string one
    op.drop_column('project_members', 'role')
    op.alter_column('project_members', 'role_str',
        new_column_name='role',
        nullable=False,
        server_default=sa.text("'member'")
    ) 