"""add file attachments table

Revision ID: add_file_attachments
Revises: 
Create Date: 2023-11-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_file_attachments'
down_revision = None  # Set this to the previous migration ID if there is one
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'file_attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('original_filename', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_file_attachments_id'), 'file_attachments', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_file_attachments_id'), table_name='file_attachments')
    op.drop_table('file_attachments') 