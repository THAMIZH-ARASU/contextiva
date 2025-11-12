"""Create documents table with semantic versioning support.

Revision ID: 20251107_01
Revises: 20251106_03
Create Date: 2025-11-07
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251107_01"
down_revision = "20251106_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create documents table."""
    op.execute(
        """
        CREATE TABLE documents (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name VARCHAR(500) NOT NULL,
            type VARCHAR(50) NOT NULL,
            version VARCHAR(20) NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )

    # Create indexes for performance
    op.execute("CREATE INDEX idx_documents_project_id ON documents(project_id);")
    op.execute("CREATE INDEX idx_documents_version ON documents(version);")
    op.execute("CREATE INDEX idx_documents_content_hash ON documents(content_hash);")
    op.execute(
        "CREATE INDEX idx_documents_project_name ON documents(project_id, name);"
    )


def downgrade() -> None:
    """Drop documents table."""
    op.execute("DROP TABLE IF EXISTS documents CASCADE;")
