"""create users table

Revision ID: 20251106_03
Revises: 20251106_02
Create Date: 2025-11-06

"""
from alembic import op


# revision identifiers
revision = '20251106_03'
down_revision = '20251106_02'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            roles TEXT[] NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    
    # Create indexes for fast lookup
    op.execute("CREATE INDEX idx_users_username ON users(username)")
    op.execute("CREATE INDEX idx_users_email ON users(email)")
    
    # Insert test user for development (username: testuser, password: testpass)
    # Password hash generated using bcrypt for "testpass"
    op.execute("""
        INSERT INTO users (username, email, hashed_password, is_active, roles)
        VALUES (
            'testuser',
            'testuser@example.com',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7MvXJLEkOq',
            true,
            ARRAY['user']
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS users CASCADE")
