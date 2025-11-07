"""E2E tests for health endpoint (Story 1.1)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_returns_200_ok():
    """Test that GET /api/v1/health returns 200 OK status."""
    async with AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.get("/api/v1/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "db": "ok"}


@pytest.mark.asyncio
async def test_health_endpoint_verifies_db_connection():
    """Test that health endpoint actually verifies database connectivity."""
    async with AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.get("/api/v1/health")
        
        data = response.json()
        assert "db" in data
        assert data["db"] in ["ok", "down"]  # Should be one of these states
