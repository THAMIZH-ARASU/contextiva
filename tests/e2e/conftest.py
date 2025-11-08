"""E2E test configuration."""

import asyncio

import pytest
import pytest_asyncio
from src.shared.infrastructure.database.connection import close_pool


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
    """Clean up database pool after each test."""
    yield
    await close_pool()
