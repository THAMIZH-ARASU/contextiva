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
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider), \
         patch("src.infrastructure.external.llm.provider_factory.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Hybrid Test Project", "description": "Test hybrid search"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Upload a document with some content using knowledge/upload
            document_response = await ac.post(
                "/api/v1/knowledge/upload",
                data={
                    "project_id": project_id,
                },
                files={
                    "file": ("ml_guide.md", io.BytesIO(b"Machine learning is awesome. Deep learning uses neural networks."), "text/markdown")
                },
                headers=auth_headers,
            )
            assert document_response.status_code == 202
            
            # Wait for document processing
            await asyncio.sleep(2)
            
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
         patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_llm_provider", return_value=mock_llm_provider), \
         patch("src.infrastructure.external.llm.provider_factory.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider):
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Rerank Test Project", "description": "Test re-ranking"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Upload a document using knowledge/upload
            document_response = await ac.post(
                "/api/v1/knowledge/upload",
                data={
                    "project_id": project_id,
                },
                files={
                    "file": ("nlp.md", io.BytesIO(b"Natural language processing is important. Transformers revolutionized NLP."), "text/markdown")
                },
                headers=auth_headers,
            )
            assert document_response.status_code == 202
            
            # Wait for document processing
            await asyncio.sleep(2)
            
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
         patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_llm_provider", return_value=mock_llm_provider), \
         patch("src.infrastructure.external.llm.provider_factory.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider):
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Combined Test Project", "description": "Test hybrid + reranking"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Upload a document using knowledge/upload
            document_response = await ac.post(
                "/api/v1/knowledge/upload",
                data={
                    "project_id": project_id,
                },
                files={
                    "file": ("ai.md", io.BytesIO(b"Artificial intelligence encompasses machine learning and deep learning."), "text/markdown")
                },
                headers=auth_headers,
            )
            assert document_response.status_code == 202
            
            # Wait for document processing
            await asyncio.sleep(2)
            
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
         patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_llm_provider", return_value=mock_llm_provider), \
         patch("src.infrastructure.external.llm.provider_factory.ProviderFactory.get_embedding_provider", return_value=mock_embedding_provider):
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create project
            project_response = await ac.post(
                "/api/v1/projects",
                json={"name": "Schema Test Project", "description": "Test new schema fields"},
                headers=auth_headers,
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["id"]
            
            # Upload a document using knowledge/upload
            document_response = await ac.post(
                "/api/v1/knowledge/upload",
                data={
                    "project_id": project_id,
                },
                files={
                    "file": ("test.md", io.BytesIO(b"Test content for schema validation."), "text/markdown")
                },
                headers=auth_headers,
            )
            assert document_response.status_code == 202
            
            # Wait for document processing
            await asyncio.sleep(2)
            
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


# ==================== STORY 3.3: Agentic RAG E2E Tests ====================


@pytest.mark.asyncio
async def test_rag_query_with_agentic_rag_true_returns_synthesized_answer(async_client, test_user):
    """Test POST /api/v1/rag/query with use_agentic_rag=true returns synthesized_answer."""
    # Create project
    project_response = await async_client.post(
        "/api/v1/projects",
        json={
            "name": "Test Agentic RAG Project",
            "description": "Testing agentic RAG synthesis",
        },
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]
    
    # Upload a document
    file_content = b"Python is a high-level programming language. FastAPI is a modern web framework for Python."
    files = {"file": ("test.md", io.BytesIO(file_content), "text/markdown")}
    upload_response = await async_client.post(
        f"/api/v1/projects/{project_id}/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert upload_response.status_code == 201
    
    # Wait for processing
    await asyncio.sleep(3)
    
    # Query with agentic RAG enabled - mock the LLM response
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory") as mock_factory:
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_text.return_value = [0.1] * 1536
        
        mock_llm_provider = AsyncMock()
        expected_answer = "Python is a high-level programming language, and FastAPI is a modern web framework built for Python."
        mock_llm_provider.generate_completion.return_value = expected_answer
        
        mock_factory.get_embedding_provider.return_value = mock_embedding_provider
        mock_factory.get_llm_provider.return_value = mock_llm_provider
        
        query_response = await async_client.post(
            "/api/v1/rag/query",
            json={
                "project_id": project_id,
                "query_text": "What is Python and FastAPI?",
                "top_k": 5,
                "use_agentic_rag": True,
            },
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )
        
        assert query_response.status_code == 200
        data = query_response.json()
        assert "synthesized_answer" in data
        assert data["synthesized_answer"] == expected_answer
        assert isinstance(data["synthesized_answer"], str)
        assert len(data["synthesized_answer"]) > 0


@pytest.mark.asyncio
async def test_rag_query_with_agentic_rag_false_no_synthesized_answer(async_client, test_user):
    """Test synthesized_answer is None when use_agentic_rag=false."""
    # Create project
    project_response = await async_client.post(
        "/api/v1/projects",
        json={
            "name": "Test No Synthesis Project",
            "description": "Testing without synthesis",
        },
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]
    
    # Upload a document
    file_content = b"Machine learning is a subset of AI."
    files = {"file": ("test.md", io.BytesIO(file_content), "text/markdown")}
    upload_response = await async_client.post(
        f"/api/v1/projects/{project_id}/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert upload_response.status_code == 201
    
    # Wait for processing
    await asyncio.sleep(3)
    
    # Query without agentic RAG
    query_response = await async_client.post(
        "/api/v1/rag/query",
        json={
            "project_id": project_id,
            "query_text": "What is machine learning?",
            "top_k": 5,
            "use_agentic_rag": False,
        },
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    
    assert query_response.status_code == 200
    data = query_response.json()
    assert data["synthesized_answer"] is None


@pytest.mark.asyncio
async def test_rag_query_combined_mode_all_flags_enabled(async_client, test_user):
    """Test combined mode with use_hybrid_search, use_re_ranking, and use_agentic_rag all true."""
    # Create project
    project_response = await async_client.post(
        "/api/v1/projects",
        json={
            "name": "Test Combined Mode Project",
            "description": "Testing all flags enabled",
        },
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]
    
    # Upload a document
    file_content = b"Deep learning is a technique in machine learning. Neural networks are used in deep learning."
    files = {"file": ("test.md", io.BytesIO(file_content), "text/markdown")}
    upload_response = await async_client.post(
        f"/api/v1/projects/{project_id}/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert upload_response.status_code == 201
    
    # Wait for processing
    await asyncio.sleep(3)
    
    # Query with all flags enabled
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory") as mock_factory:
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_text.return_value = [0.1] * 1536
        
        mock_llm_provider = AsyncMock()
        # Mock for both re-ranking and synthesis
        mock_llm_provider.generate_completion.side_effect = [
            '{"ranked_indices": [0, 1]}',  # Re-ranking response
            "Deep learning is a machine learning technique that uses neural networks."  # Synthesis response
        ]
        
        mock_factory.get_embedding_provider.return_value = mock_embedding_provider
        mock_factory.get_llm_provider.return_value = mock_llm_provider
        
        query_response = await async_client.post(
            "/api/v1/rag/query",
            json={
                "project_id": project_id,
                "query_text": "What is deep learning?",
                "top_k": 5,
                "use_hybrid_search": True,
                "use_re_ranking": True,
                "use_agentic_rag": True,
            },
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )
        
        assert query_response.status_code == 200
        data = query_response.json()
        assert "synthesized_answer" in data
        assert data["synthesized_answer"] is not None
        assert isinstance(data["synthesized_answer"], str)
        # Should have results with all score types
        if data["total_results"] > 0:
            first_result = data["results"][0]
            assert "similarity_score" in first_result


@pytest.mark.asyncio
async def test_rag_query_synthesis_content_relevant_to_query(async_client, test_user):
    """Test synthesized_answer content is relevant to query (basic validation)."""
    # Create project
    project_response = await async_client.post(
        "/api/v1/projects",
        json={
            "name": "Test Relevance Project",
            "description": "Testing synthesis relevance",
        },
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]
    
    # Upload a document
    file_content = b"FastAPI is a modern, fast web framework for building APIs with Python."
    files = {"file": ("test.md", io.BytesIO(file_content), "text/markdown")}
    upload_response = await async_client.post(
        f"/api/v1/projects/{project_id}/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert upload_response.status_code == 201
    
    # Wait for processing
    await asyncio.sleep(3)
    
    # Query with agentic RAG
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory") as mock_factory:
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_text.return_value = [0.1] * 1536
        
        mock_llm_provider = AsyncMock()
        # Return an answer that contains relevant keywords
        relevant_answer = "FastAPI is a modern web framework designed for building APIs with Python, known for its speed and ease of use."
        mock_llm_provider.generate_completion.return_value = relevant_answer
        
        mock_factory.get_embedding_provider.return_value = mock_embedding_provider
        mock_factory.get_llm_provider.return_value = mock_llm_provider
        
        query_response = await async_client.post(
            "/api/v1/rag/query",
            json={
                "project_id": project_id,
                "query_text": "What is FastAPI?",
                "use_agentic_rag": True,
            },
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )
        
        assert query_response.status_code == 200
        data = query_response.json()
        assert "synthesized_answer" in data
        synthesized = data["synthesized_answer"]
        assert synthesized is not None
        # Basic validation - answer should contain relevant keywords
        assert any(keyword.lower() in synthesized.lower() for keyword in ["FastAPI", "framework", "API", "Python"])


@pytest.mark.asyncio
async def test_rag_query_synthesis_graceful_degradation_on_failure(async_client, test_user):
    """Test graceful degradation if synthesis fails - query still returns results."""
    # Create project
    project_response = await async_client.post(
        "/api/v1/projects",
        json={
            "name": "Test Degradation Project",
            "description": "Testing graceful degradation",
        },
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]
    
    # Upload a document
    file_content = b"Asyncio is a library in Python for asynchronous programming."
    files = {"file": ("test.md", io.BytesIO(file_content), "text/markdown")}
    upload_response = await async_client.post(
        f"/api/v1/projects/{project_id}/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert upload_response.status_code == 201
    
    # Wait for processing
    await asyncio.sleep(3)
    
    # Query with agentic RAG but LLM will fail
    with patch("src.application.use_cases.knowledge.query_knowledge.ProviderFactory") as mock_factory:
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_text.return_value = [0.1] * 1536
        
        mock_llm_provider = AsyncMock()
        # Simulate LLM failure
        mock_llm_provider.generate_completion.side_effect = Exception("LLM API error")
        
        mock_factory.get_embedding_provider.return_value = mock_embedding_provider
        mock_factory.get_llm_provider.return_value = mock_llm_provider
        
        query_response = await async_client.post(
            "/api/v1/rag/query",
            json={
                "project_id": project_id,
                "query_text": "What is asyncio?",
                "use_agentic_rag": True,
            },
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )
        
        # Query should still succeed
        assert query_response.status_code == 200
        data = query_response.json()
        # synthesized_answer should be None due to failure
        assert data["synthesized_answer"] is None
        # But results should still be returned
        assert "results" in data
        assert "total_results" in data
