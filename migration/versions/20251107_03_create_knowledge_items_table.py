"""Create knowledge_items table with pgvector support for embeddings.

Revision ID: 20251107_03
Revises: 20251107_02
Create Date: 2025-11-07
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251107_03"
down_revision = "20251107_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create knowledge_items table with vector embeddings."""
    op.execute(
        """
        CREATE TABLE knowledge_items (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_text TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            embedding vector(1536) NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )

    # Create indexes for performance
    op.execute(
        "CREATE INDEX idx_knowledge_items_document_id ON knowledge_items(document_id);"
    )
    op.execute(
        "CREATE INDEX idx_knowledge_items_chunk_index ON knowledge_items(document_id, chunk_index);"
    )

    # Create HNSW vector index for fast similarity search
    # Using cosine distance as the default operator
    op.execute(
        """
        CREATE INDEX idx_knowledge_items_embedding_hnsw 
        ON knowledge_items 
        USING hnsw (embedding vector_cosine_ops);
        """
    )


def downgrade() -> None:
    """Drop knowledge_items table."""
    op.execute("DROP TABLE IF EXISTS knowledge_items CASCADE;")
