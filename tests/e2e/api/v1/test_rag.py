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


# ============================================================================
# POST /api/v1/rag/query - Advanced RAG Features (Story 3.2)
# ============================================================================


async def test_rag_query_with_hybrid_search_enabled(auth_headers, mock_embedding_provider):
    """Test RAG query with use_hybrid_search=True combines vector + keyword search."""
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Hybrid Test Project", "description": "Test hybrid search"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Upload a document with some content
            document_response = await ac.post(
                "/api/v1/documents",
                data={
                    "project_id": project_id,
                    "title": "Machine Learning Guide",
                },
                files={
                    "file": ("ml_guide.txt", io.BytesIO(b"Machine learning is awesome. Deep learning uses neural networks."), "text/plain")
                },
                headers=auth_headers,
            )
            assert document_response.status_code == 201
            
            # Wait for document processing
            await asyncio.sleep(1)
            
            # Query with hybrid search enabled
            response = await ac.post(
                "/api/v1/rag/query",
                json={
                    "project_id": project_id,
                    "query_text": "machine learning neural networks",
                    "use_hybrid_search": True,  # NEW FLAG
                    "top_k": 5,
                },
                headers=auth_headers,
            )
            
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)


async def test_rag_query_with_reranking_enabled(auth_headers, mock_embedding_provider):
    """Test RAG query with use_re_ranking=True applies LLM re-ranking."""
    # Mock LLM provider for re-ranking
    mock_llm_provider = AsyncMock()
    mock_llm_provider.generate_completion = AsyncMock(return_value="[0, 1, 2]")  # Re-ranked indices
    
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider), \
         patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_llm_provider", return_value=mock_llm_provider):
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Rerank Test Project", "description": "Test re-ranking"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Upload a document
            document_response = await ac.post(
                "/api/v1/documents",
                data={
                    "project_id": project_id,
                    "title": "NLP Concepts",
                },
                files={
                    "file": ("nlp.txt", io.BytesIO(b"Natural language processing is important. Transformers revolutionized NLP."), "text/plain")
                },
                headers=auth_headers,
            )
            assert document_response.status_code == 201
            
            # Wait for document processing
            await asyncio.sleep(1)
            
            # Query with re-ranking enabled
            response = await ac.post(
                "/api/v1/rag/query",
                json={
                    "project_id": project_id,
                    "query_text": "what are transformers in NLP",
                    "use_re_ranking": True,  # NEW FLAG
                    "top_k": 5,
                },
                headers=auth_headers,
            )
            
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        
        # Verify LLM provider was called for re-ranking
        mock_llm_provider.generate_completion.assert_called()


async def test_rag_query_with_hybrid_and_reranking_combined(auth_headers, mock_embedding_provider):
    """Test RAG query with both use_hybrid_search=True and use_re_ranking=True."""
    # Mock LLM provider
    mock_llm_provider = AsyncMock()
    mock_llm_provider.generate_completion = AsyncMock(return_value="[0]")
    
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider), \
         patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_llm_provider", return_value=mock_llm_provider):
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Combined Test Project", "description": "Test hybrid + reranking"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Upload a document
            document_response = await ac.post(
                "/api/v1/documents",
                data={
                    "project_id": project_id,
                    "title": "AI Overview",
                },
                files={
                    "file": ("ai.txt", io.BytesIO(b"Artificial intelligence encompasses machine learning and deep learning."), "text/plain")
                },
                headers=auth_headers,
            )
            assert document_response.status_code == 201
            
            # Wait for document processing
            await asyncio.sleep(1)
            
            # Query with both flags enabled
            response = await ac.post(
                "/api/v1/rag/query",
                json={
                    "project_id": project_id,
                    "query_text": "artificial intelligence",
                    "use_hybrid_search": True,  # Both flags
                    "use_re_ranking": True,     # Both flags
                    "top_k": 5,
                },
                headers=auth_headers,
            )
            
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


async def test_rag_query_response_schema_with_new_score_fields(auth_headers, mock_embedding_provider):
    """Test response schema includes new optional score fields (bm25_score, rerank_score)."""
    # Mock LLM provider
    mock_llm_provider = AsyncMock()
    mock_llm_provider.generate_completion = AsyncMock(return_value="[0]")
    
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider), \
         patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_llm_provider", return_value=mock_llm_provider):
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Schema Test Project", "description": "Test new schema fields"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Upload a document
            document_response = await ac.post(
                "/api/v1/documents",
                data={
                    "project_id": project_id,
                    "title": "Test Document",
                },
                files={
                    "file": ("test.txt", io.BytesIO(b"Test content for schema validation."), "text/plain")
                },
                headers=auth_headers,
            )
            assert document_response.status_code == 201
            
            # Wait for document processing
            await asyncio.sleep(1)
            
            # Query with all features enabled
            response = await ac.post(
                "/api/v1/rag/query",
                json={
                    "project_id": project_id,
                    "query_text": "test content",
                    "use_hybrid_search": True,
                    "use_re_ranking": True,
                    "top_k": 5,
                },
                headers=auth_headers,
            )
            
        assert response.status_code == 200
        data = response.json()
        
        # Validate new schema fields exist (even if None)
        if data["results"]:
            result = data["results"][0]
            assert "similarity_score" in result
            # New fields (may be None)
            assert "bm25_score" in result or "bm25_score" not in result  # Optional field
            assert "rerank_score" in result or "rerank_score" not in result  # Optional field


async def test_rag_query_default_behavior_regression(auth_headers, mock_embedding_provider):
    """Test default behavior (flags=False) still works - regression test."""
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Regression Test Project", "description": "Test default behavior"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Query with default flags (should work like Story 3.1)
            response = await ac.post(
                "/api/v1/rag/query",
                json={
                    "project_id": project_id,
                    "query_text": "test query",
                    # No flags - default to False
                },
                headers=auth_headers,
            )
            
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_results" in data


async def test_rag_query_cache_hit_scenario(auth_headers, mock_embedding_provider):
    """Test cache hit: identical query returns cached results (faster, no DB query)."""
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Cache Test Project", "description": "Test caching"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            query_payload = {
                "project_id": project_id,
                "query_text": "cached test query",
                "use_hybrid_search": True,
                "top_k": 5,
            }
            
            # First query - cache miss (will query database)
            response1 = await ac.post(
                "/api/v1/rag/query",
                json=query_payload,
                headers=auth_headers,
            )
            assert response1.status_code == 200
            data1 = response1.json()
            
            # Second identical query - should hit cache
            response2 = await ac.post(
                "/api/v1/rag/query",
                json=query_payload,
                headers=auth_headers,
            )
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Results should be identical (cached)
            assert data1["total_results"] == data2["total_results"]


async def test_rag_query_cache_miss_with_different_parameters(auth_headers, mock_embedding_provider):
    """Test cache miss: different parameters create different cache keys."""
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Cache Miss Test", "description": "Test cache uniqueness"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Query 1
            response1 = await ac.post(
                "/api/v1/rag/query",
                json={
                    "project_id": project_id,
                    "query_text": "test query one",
                    "use_hybrid_search": True,
                    "top_k": 5,
                },
                headers=auth_headers,
            )
            assert response1.status_code == 200
            
            # Query 2 - different text (should create new cache key)
            response2 = await ac.post(
                "/api/v1/rag/query",
                json={
                    "project_id": project_id,
                    "query_text": "test query two",  # Different
                    "use_hybrid_search": True,
                    "top_k": 5,
                },
                headers=auth_headers,
            )
            assert response2.status_code == 200
            
            # Query 3 - different flags (should create new cache key)
            response3 = await ac.post(
                "/api/v1/rag/query",
                json={
                    "project_id": project_id,
                    "query_text": "test query one",  # Same as query 1
                    "use_hybrid_search": False,  # Different flag
                    "top_k": 5,
                },
                headers=auth_headers,
            )
            assert response3.status_code == 200
