"""add pgvector extension

Revision ID: add_pgvector_001
Revises: add_time_entries_001
Create Date: 2024-05-27 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_pgvector_001'
down_revision = 'add_time_entries_001'
branch_labels = None
depends_on = None

def upgrade():
    # Enable the vector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create tables that will use vector columns
    op.create_table(
        'embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('embedding', sa.String(), nullable=False),  # Will store vector as string initially
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_embeddings_entity_type', 'embeddings', ['entity_type'])
    op.create_index('ix_embeddings_entity_id', 'embeddings', ['entity_id'])
    op.create_index('ix_embeddings_model', 'embeddings', ['model'])
    
    # Add vector column using raw SQL (after extension is enabled)
    op.execute('ALTER TABLE embeddings ADD COLUMN embedding_vector vector(1536)')

def downgrade():
    # Drop the tables
    op.drop_table('embeddings')
    
    # Disable the vector extension
    op.execute('DROP EXTENSION IF EXISTS vector') 