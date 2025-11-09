"""E2E tests for RAG query endpoint."""

import asyncio
import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

from src.api.main import app


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def auth_token() -> str:
    """Get authentication token for test user."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/token",
            data={"username": "testuser", "password": "testpass"},
        )
        assert response.status_code == 200
        return response.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict[str, str]:
    """Get authorization headers with bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def mock_embedding_provider():
    """Mock embedding provider to return fake embeddings."""
    mock_provider = AsyncMock()
    # Return a 1536-dimensional vector (standard for many models)
    mock_provider.embed_text.return_value = [0.1] * 1536
    return mock_provider


# ============================================================================
# POST /api/v1/rag/query - RAG Query Endpoint Tests
# ============================================================================


async def test_rag_query_unauthorized():
    """Test request without JWT token returns 401."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/rag/query",
            json={
                "project_id": str(uuid4()),
                "query_text": "test query",
            },
        )
    assert response.status_code == 401


async def test_rag_query_invalid_project_id(auth_headers, mock_embedding_provider):
    """Test query with invalid project_id returns 404."""
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/rag/query",
                json={
                    "project_id": str(uuid4()),  # Non-existent project
                    "query_text": "test query",
                },
                headers=auth_headers,
            )
        assert response.status_code == 404


async def test_rag_query_empty_string_validation(auth_headers):
    """Test query_text validation: empty string returns 422."""
    # Create a project first
    async with AsyncClient(app=app, base_url="http://test") as ac:
        project_response = await ac.post(
            "/api/v1/projects",
            json={"name": "Test Project", "description": "Test"},
            headers=auth_headers,
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]
        
        # Try to query with empty string
        response = await ac.post(
            "/api/v1/rag/query",
            json={
                "project_id": project_id,
                "query_text": "",  # Empty string should fail validation
            },
            headers=auth_headers,
        )
    assert response.status_code == 422


async def test_rag_query_exceeds_max_length(auth_headers):
    """Test query_text validation: exceeds max length returns 422."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        project_response = await ac.post(
            "/api/v1/projects",
            json={"name": "Test Project", "description": "Test"},
            headers=auth_headers,
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]
        
        # Try to query with text exceeding max length
        response = await ac.post(
            "/api/v1/rag/query",
            json={
                "project_id": project_id,
                "query_text": "x" * 10001,  # Exceeds max_length=10000
            },
            headers=auth_headers,
        )
    assert response.status_code == 422


async def test_rag_query_success_with_default_top_k(auth_headers, mock_embedding_provider):
    """Test successful RAG query with default top_k (5)."""
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Test Project", "description": "Test"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Query without specifying top_k (should default to 5)
            response = await ac.post(
                "/api/v1/rag/query",
                json={
                    "project_id": project_id,
                    "query_text": "test content",
                },
                headers=auth_headers,
            )
            
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_results" in data
        assert isinstance(data["results"], list)


async def test_rag_query_custom_top_k(auth_headers, mock_embedding_provider):
    """Test top_k parameter: custom value is accepted."""
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Test Project", "description": "Test"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Query with custom top_k
            response = await ac.post(
                "/api/v1/rag/query",
                json={
                    "project_id": project_id,
                    "query_text": "test content",
                    "top_k": 3,
                },
                headers=auth_headers,
            )
            
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 3  # Should respect top_k


async def test_rag_query_exceeds_max_top_k_returns_capped_results(auth_headers, mock_embedding_provider):
    """Test top_k parameter: exceeds max returns capped results."""
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Test Project", "description": "Test"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Query with excessive top_k (should be capped at max_top_k = 50)
            response = await ac.post(
                "/api/v1/rag/query",
                json={
                    "project_id": project_id,
                    "query_text": "test",
                    "top_k": 100,  # Exceeds max
                },
                headers=auth_headers,
            )
            
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 50  # Capped at max_top_k


async def test_rag_query_response_schema_validation(auth_headers, mock_embedding_provider):
    """Test response schema has all required fields."""
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Test Project", "description": "Test"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Query
            response = await ac.post(
                "/api/v1/rag/query",
                json={
                    "project_id": project_id,
                    "query_text": "test",
                },
                headers=auth_headers,
            )
            
        assert response.status_code == 200
        data = response.json()
        
        # Validate response schema
        assert "results" in data
        assert "total_results" in data
        assert isinstance(data["results"], list)
        assert isinstance(data["total_results"], int)
        
        # If results exist, validate result schema
        for result in data["results"]:
            assert "id" in result
            assert "chunk_text" in result
            assert "similarity_score" in result
            assert "metadata" in result
            assert "document_id" in result
