"""E2E test configuration."""

import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio
from src.shared.infrastructure.database.connection import close_pool, init_pool
from src.shared.utils.security import get_password_hash


pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set the event loop policy for the test session."""
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="function")
def event_loop(event_loop_policy):
    """Create a new event loop for each test function."""
    loop = event_loop_policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_pool():
    """Clean up database pool after each test to ensure fresh event loop for next test."""
    yield
    # Close pool after test
    await close_pool()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def test_user():
    """Ensure a test user exists for authentication in E2E tests."""
    pool = await init_pool()
    user_id = uuid4()
    
    # Create test user (upsert pattern - create if not exists)
    async with pool.acquire() as conn:
        # Check if user already exists
        existing = await conn.fetchval(
            "SELECT id FROM users WHERE username = $1", "testuser"
        )
        
        if not existing:
            await conn.execute(
                """
                INSERT INTO users (id, username, email, hashed_password, is_active)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id,
                "testuser",
                "test@example.com",
                get_password_hash("testpass"),
                True,
            )
        else:
            user_id = existing
    
    yield user_id
    # No teardown needed - user persists across tests
