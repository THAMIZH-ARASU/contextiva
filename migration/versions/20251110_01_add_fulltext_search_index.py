"""Add full-text search GIN index on knowledge_items.chunk_text.

Revision ID: 20251110_01
Revises: 20251107_03
Create Date: 2025-11-10
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251110_01"
down_revision = "20251107_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add GIN index for full-text search on chunk_text."""
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_knowledge_items_fulltext 
        ON knowledge_items 
        USING gin(to_tsvector('english', chunk_text));
        """
    )


def downgrade() -> None:
    """Drop full-text search index."""
    op.execute("DROP INDEX IF EXISTS idx_knowledge_items_fulltext;")
