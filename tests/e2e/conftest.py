"""E2E test configuration."""

import pytest
import pytest_asyncio


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="function")
def event_loop():
    """Create an event loop for each test."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
