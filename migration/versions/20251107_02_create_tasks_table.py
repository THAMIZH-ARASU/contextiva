"""Create tasks table with status, priority, and dependency tracking.

Revision ID: 20251107_02
Revises: 20251107_01
Create Date: 2025-11-07
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251107_02"
down_revision = "20251107_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tasks table."""
    op.execute(
        """
        CREATE TABLE tasks (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            status VARCHAR(50) NOT NULL,
            priority VARCHAR(50) NOT NULL,
            assignee VARCHAR(200),
            dependencies UUID[],
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )

    # Create indexes for performance
    op.execute("CREATE INDEX idx_tasks_project_id ON tasks(project_id);")
    op.execute("CREATE INDEX idx_tasks_status ON tasks(status);")
    op.execute("CREATE INDEX idx_tasks_assignee ON tasks(assignee);")
    op.execute("CREATE INDEX idx_tasks_project_status ON tasks(project_id, status);")


def downgrade() -> None:
    """Drop tasks table."""
    op.execute("DROP TABLE IF EXISTS tasks CASCADE;")
