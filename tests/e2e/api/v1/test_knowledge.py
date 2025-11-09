"""E2E tests for Knowledge Upload API endpoints."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.infrastructure.external.llm.provider_factory import ProviderFactory
from src.shared.infrastructure.database.connection import init_pool

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def cleanup_knowledge():
    """Clean up knowledge_items and documents tables before and after each test."""
    # Setup - clean before test
    pool = await init_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM knowledge_items")
        await conn.execute("DELETE FROM documents")
    
    yield
    
    # Teardown - clean after test
    # Pool is re-initialized by cleanup_pool fixture, so init_pool() returns fresh pool
    pool = await init_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM knowledge_items")
        await conn.execute("DELETE FROM documents")


@pytest.fixture
def mock_llm_provider():
    """Mock the LLM provider to avoid needing Ollama running."""
    # Return a fake embedding vector (1536 dimensions for OpenAI compatibility)
    fake_embedding = [0.1] * 1536
    
    with patch("src.infrastructure.external.llm.provider_factory.ProviderFactory.get_embedding_provider") as mock:
        mock_provider = AsyncMock()
        mock_provider.embed_text.return_value = fake_embedding
        mock.return_value = mock_provider
        yield mock_provider


@pytest_asyncio.fixture
async def test_project_id() -> UUID:
    """Create a test project and return its ID."""
    pool = await init_pool()
    project_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO projects (id, name, status)
            VALUES ($1, $2, $3)
            """,
            project_id,
            "Test Knowledge Project",
            "Active",
        )
    yield project_id
    # Cleanup
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM projects WHERE id = $1", project_id)


@pytest_asyncio.fixture
async def auth_token() -> str:
    """Get authentication token for test user."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
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


# ============================================================================
# POST /api/v1/knowledge/upload - Upload Knowledge File
# ============================================================================


async def test_upload_knowledge_markdown_success(
    cleanup_knowledge, test_project_id, auth_headers, mock_llm_provider
):
    """Test uploading a markdown file returns 202 and creates document."""
    fixtures_path = Path(__file__).parent.parent.parent.parent / "fixtures" / "sample_files"
    md_file = fixtures_path / "sample.md"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with open(md_file, "rb") as f:
            response = await ac.post(
                "/api/v1/knowledge/upload",
                files={"file": ("sample.md", f, "text/markdown")},
                data={"project_id": str(test_project_id)},
                headers=auth_headers,
            )

    assert response.status_code == 202
    data = response.json()
    assert "document_id" in data
    assert data["status"] == "processing"
    assert "sample.md" in data["message"]

    # Verify document was created
    pool = await init_pool()
    async with pool.acquire() as conn:
        doc = await conn.fetchrow(
            "SELECT * FROM documents WHERE id = $1", UUID(data["document_id"])
        )
        assert doc is not None
        assert doc["name"] == "sample.md"
        assert doc["type"] == "markdown"


async def test_upload_knowledge_html_success(cleanup_knowledge, test_project_id, auth_headers, mock_llm_provider):
    """Test uploading an HTML file processes correctly."""
    fixtures_path = Path(__file__).parent.parent.parent.parent / "fixtures" / "sample_files"
    html_file = fixtures_path / "sample.html"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with open(html_file, "rb") as f:
            response = await ac.post(
                "/api/v1/knowledge/upload",
                files={"file": ("sample.html", f, "text/html")},
                data={"project_id": str(test_project_id)},
                headers=auth_headers,
            )

    assert response.status_code == 202
    data = response.json()
    assert "document_id" in data
    assert data["status"] == "processing"


async def test_upload_knowledge_unauthorized(cleanup_knowledge, test_project_id):
    """Test uploading without auth token returns 401."""
    fixtures_path = Path(__file__).parent.parent.parent.parent / "fixtures" / "sample_files"
    md_file = fixtures_path / "sample.md"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with open(md_file, "rb") as f:
            response = await ac.post(
                "/api/v1/knowledge/upload",
                files={"file": ("sample.md", f, "text/markdown")},
                data={"project_id": str(test_project_id)},
            )

    assert response.status_code == 401


async def test_upload_knowledge_invalid_file_type(
    cleanup_knowledge, test_project_id, auth_headers
):
    """Test uploading unsupported file type returns 422."""
    # Create a temporary .txt file
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp.write("Test content")
        tmp_path = tmp.name

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            with open(tmp_path, "rb") as f:
                response = await ac.post(
                    "/api/v1/knowledge/upload",
                    files={"file": ("test.txt", f, "text/plain")},
                    data={"project_id": str(test_project_id)},
                    headers=auth_headers,
                )

        assert response.status_code == 422
        assert "Unsupported file type" in response.json()["detail"]
    finally:
        Path(tmp_path).unlink()


async def test_upload_knowledge_file_too_large(
    cleanup_knowledge, test_project_id, auth_headers
):
    """Test uploading file exceeding size limit returns 413."""
    # Create a large temporary file (>10MB)
    import tempfile

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".md", delete=False) as tmp:
        # Write 11MB of data
        tmp.write(b"a" * (11 * 1024 * 1024))
        tmp_path = tmp.name

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            with open(tmp_path, "rb") as f:
                response = await ac.post(
                    "/api/v1/knowledge/upload",
                    files={"file": ("large.md", f, "text/markdown")},
                    data={"project_id": str(test_project_id)},
                    headers=auth_headers,
                )

        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"]
    finally:
        Path(tmp_path).unlink()


async def test_upload_knowledge_creates_knowledge_items(
    cleanup_knowledge, test_project_id, auth_headers, mock_llm_provider
):
    """Test that upload creates knowledge items in the database."""
    fixtures_path = Path(__file__).parent.parent.parent.parent / "fixtures" / "sample_files"
    md_file = fixtures_path / "sample.md"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with open(md_file, "rb") as f:
            response = await ac.post(
                "/api/v1/knowledge/upload",
                files={"file": ("sample.md", f, "text/markdown")},
                data={"project_id": str(test_project_id)},
                headers=auth_headers,
            )

    assert response.status_code == 202
    document_id = UUID(response.json()["document_id"])

    # Wait a bit for background processing (in our case it's synchronous for testing)
    await asyncio.sleep(0.1)

    # Verify knowledge items were created
    pool = await init_pool()
    async with pool.acquire() as conn:
        items = await conn.fetch(
            "SELECT * FROM knowledge_items WHERE document_id = $1", document_id
        )
        assert len(items) > 0, "Should have created at least one knowledge item"

        # Verify chunk has metadata
        first_item = items[0]
        assert first_item["chunk_text"] is not None
        assert first_item["embedding"] is not None
        assert first_item["metadata"] is not None
        assert "chunk_index" in first_item["metadata"]


async def test_upload_knowledge_chunking(cleanup_knowledge, test_project_id, auth_headers, mock_llm_provider):
    """Test that chunks are properly created with metadata."""
    fixtures_path = Path(__file__).parent.parent.parent.parent / "fixtures" / "sample_files"
    md_file = fixtures_path / "sample.md"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with open(md_file, "rb") as f:
            response = await ac.post(
                "/api/v1/knowledge/upload",
                files={"file": ("sample.md", f, "text/markdown")},
                data={"project_id": str(test_project_id)},
                headers=auth_headers,
            )

    assert response.status_code == 202
    document_id = UUID(response.json()["document_id"])

    # Verify chunks have proper metadata structure
    pool = await init_pool()
    async with pool.acquire() as conn:
        items = await conn.fetch(
            "SELECT * FROM knowledge_items WHERE document_id = $1 ORDER BY chunk_index",
            document_id,
        )

        for idx, item in enumerate(items):
            assert item["chunk_index"] == idx
            import json
            metadata = json.loads(item["metadata"]) if isinstance(item["metadata"], str) else item["metadata"]
            assert "start_char" in metadata
            assert "end_char" in metadata
            assert "token_count" in metadata
            assert metadata["start_char"] >= 0
            assert metadata["end_char"] > metadata["start_char"]
            assert metadata["token_count"] > 0


async def test_upload_knowledge_embedding(cleanup_knowledge, test_project_id, auth_headers, mock_llm_provider):
    """Test that embeddings are generated and stored."""
    fixtures_path = Path(__file__).parent.parent.parent.parent / "fixtures" / "sample_files"
    md_file = fixtures_path / "sample.md"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with open(md_file, "rb") as f:
            response = await ac.post(
                "/api/v1/knowledge/upload",
                files={"file": ("sample.md", f, "text/markdown")},
                data={"project_id": str(test_project_id)},
                headers=auth_headers,
            )

    assert response.status_code == 202
    document_id = UUID(response.json()["document_id"])

    # Verify embeddings exist and are valid
    pool = await init_pool()
    async with pool.acquire() as conn:
        items = await conn.fetch(
            "SELECT * FROM knowledge_items WHERE document_id = $1", document_id
        )

        for item in items:
            embedding = item["embedding"]
            assert embedding is not None
            assert len(embedding) > 0, "Embedding should have dimensions"
            # Verify it's a list of floats (pgvector returns as string, convert to list)
            if isinstance(embedding, str):
                # Parse the vector string format: "[0.1,0.2,...]"
                embedding_list = eval(embedding)
                assert all(isinstance(val, (int, float)) for val in embedding_list)
            else:
                # Already a list
                assert all(isinstance(val, (int, float)) for val in embedding)


# ============================================================================
# POST /api/v1/knowledge/crawl - Crawl Knowledge from URL
# ============================================================================


async def test_crawl_knowledge_success(
    cleanup_knowledge, test_project_id, auth_headers, mock_llm_provider
):
    """Test crawling a valid URL returns 202 and creates document."""
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Crawl Page</title>
        <meta name="description" content="Test page description">
    </head>
    <body>
        <h1>Main Heading</h1>
        <p>This is test content for crawling.</p>
    </body>
    </html>
    """
    
    test_url = "https://example.com/test-page"
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with patch("src.infrastructure.external.crawler.crawler_client.httpx.AsyncClient") as mock_client:
            # Mock robots.txt response (404 = allow)
            mock_robots_response = AsyncMock()
            mock_robots_response.status_code = 404
            
            # Mock HTML fetch response
            mock_html_response = AsyncMock()
            mock_html_response.text = sample_html
            mock_html_response.raise_for_status = AsyncMock()
            
            # Setup mock to return different responses based on URL
            async def mock_get(url, **kwargs):
                if "robots.txt" in url:
                    return mock_robots_response
                return mock_html_response
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            
            response = await ac.post(
                "/api/v1/knowledge/crawl",
                json={
                    "url": test_url,
                    "project_id": str(test_project_id),
                    "respect_robots_txt": True,
                },
                headers=auth_headers,
            )

    assert response.status_code == 202
    data = response.json()
    assert "document_id" in data
    assert data["status"] == "processing"
    assert test_url in data["message"]

    # Verify document was created with WebCrawl type
    pool = await init_pool()
    async with pool.acquire() as conn:
        doc = await conn.fetchrow(
            "SELECT * FROM documents WHERE id = $1", UUID(data["document_id"])
        )
        assert doc is not None
        assert doc["type"] == "web_crawl"


async def test_crawl_knowledge_with_metadata(
    cleanup_knowledge, test_project_id, auth_headers, mock_llm_provider
):
    """Test that page title and description are extracted correctly."""
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Metadata Test Page</title>
        <meta name="description" content="This is a test description">
        <meta name="keywords" content="test, keywords">
    </head>
    <body><p>Content</p></body>
    </html>
    """
    
    test_url = "https://example.com/metadata-test"
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with patch("src.infrastructure.external.crawler.crawler_client.httpx.AsyncClient") as mock_client:
            mock_robots_response = AsyncMock()
            mock_robots_response.status_code = 404
            
            mock_html_response = AsyncMock()
            mock_html_response.text = sample_html
            mock_html_response.raise_for_status = AsyncMock()
            
            async def mock_get(url, **kwargs):
                if "robots.txt" in url:
                    return mock_robots_response
                return mock_html_response
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            
            response = await ac.post(
                "/api/v1/knowledge/crawl",
                json={
                    "url": test_url,
                    "project_id": str(test_project_id),
                },
                headers=auth_headers,
            )

    assert response.status_code == 202
    document_id = UUID(response.json()["document_id"])

    # Verify knowledge items contain metadata
    pool = await init_pool()
    async with pool.acquire() as conn:
        doc = await conn.fetchrow("SELECT * FROM documents WHERE id = $1", document_id)
        assert "Metadata Test Page" in doc["name"]
        
        items = await conn.fetch(
            "SELECT * FROM knowledge_items WHERE document_id = $1 LIMIT 1", document_id
        )
        assert len(items) > 0
        item = items[0]
        
        import json
        metadata = json.loads(item["metadata"]) if isinstance(item["metadata"], str) else item["metadata"]
        assert metadata["source_url"] == test_url
        assert metadata["page_title"] == "Metadata Test Page"


async def test_crawl_knowledge_unauthorized(test_project_id):
    """Test crawling without authentication returns 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/knowledge/crawl",
            json={
                "url": "https://example.com",
                "project_id": str(test_project_id),
            },
        )

    assert response.status_code == 401


async def test_crawl_knowledge_invalid_url(auth_headers, test_project_id):
    """Test crawling with invalid URL returns 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/knowledge/crawl",
            json={
                "url": "not-a-valid-url",
                "project_id": str(test_project_id),
            },
            headers=auth_headers,
        )

    assert response.status_code == 422


async def test_crawl_knowledge_robots_txt_allowed(
    cleanup_knowledge, test_project_id, auth_headers, mock_llm_provider
):
    """Test crawling respects robots.txt when allowed."""
    robots_txt = """
User-agent: *
Disallow: /admin/
Allow: /
"""
    
    sample_html = "<html><body><p>Allowed content</p></body></html>"
    test_url = "https://example.com/public-page"
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with patch("src.infrastructure.external.crawler.crawler_client.httpx.AsyncClient") as mock_client:
            mock_robots_response = AsyncMock()
            mock_robots_response.status_code = 200
            mock_robots_response.text = robots_txt
            mock_robots_response.raise_for_status = AsyncMock()
            
            mock_html_response = AsyncMock()
            mock_html_response.text = sample_html
            mock_html_response.raise_for_status = AsyncMock()
            
            async def mock_get(url, **kwargs):
                if "robots.txt" in url:
                    return mock_robots_response
                return mock_html_response
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            
            response = await ac.post(
                "/api/v1/knowledge/crawl",
                json={
                    "url": test_url,
                    "project_id": str(test_project_id),
                    "respect_robots_txt": True,
                },
                headers=auth_headers,
            )

    assert response.status_code == 202


async def test_crawl_knowledge_robots_txt_disallowed(
    test_project_id, auth_headers
):
    """Test crawling respects robots.txt when disallowed."""
    robots_txt = """
User-agent: *
Disallow: /
"""
    
    test_url = "https://example.com/blocked-page"
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with patch("src.infrastructure.external.crawler.crawler_client.httpx.AsyncClient") as mock_client:
            mock_robots_response = AsyncMock()
            mock_robots_response.status_code = 200
            mock_robots_response.text = robots_txt
            mock_robots_response.raise_for_status = AsyncMock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_robots_response)
            
            response = await ac.post(
                "/api/v1/knowledge/crawl",
                json={
                    "url": test_url,
                    "project_id": str(test_project_id),
                    "respect_robots_txt": True,
                },
                headers=auth_headers,
            )

    assert response.status_code == 403
    assert "robots.txt" in response.json()["detail"].lower()


async def test_crawl_knowledge_ignore_robots_txt(
    cleanup_knowledge, test_project_id, auth_headers, mock_llm_provider
):
    """Test crawling with respect_robots_txt=False bypasses robots.txt."""
    robots_txt = """
User-agent: *
Disallow: /
"""
    
    sample_html = "<html><body><p>Content despite robots.txt</p></body></html>"
    test_url = "https://example.com/ignore-robots"
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with patch("src.infrastructure.external.crawler.crawler_client.httpx.AsyncClient") as mock_client:
            # When respect_robots_txt=False, robots.txt shouldn't be checked
            mock_html_response = AsyncMock()
            mock_html_response.text = sample_html
            mock_html_response.raise_for_status = AsyncMock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_html_response)
            
            response = await ac.post(
                "/api/v1/knowledge/crawl",
                json={
                    "url": test_url,
                    "project_id": str(test_project_id),
                    "respect_robots_txt": False,
                },
                headers=auth_headers,
            )

    assert response.status_code == 202


async def test_crawl_knowledge_timeout(test_project_id, auth_headers):
    """Test handling of URL timeout."""
    import httpx
    
    test_url = "https://example.com/slow-page"
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with patch("src.infrastructure.external.crawler.crawler_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )
            
            response = await ac.post(
                "/api/v1/knowledge/crawl",
                json={
                    "url": test_url,
                    "project_id": str(test_project_id),
                },
                headers=auth_headers,
            )

    assert response.status_code == 504
    assert "timeout" in response.json()["detail"].lower()


async def test_crawl_knowledge_creates_knowledge_items(
    cleanup_knowledge, test_project_id, auth_headers, mock_llm_provider
):
    """Test that crawled content creates knowledge items."""
    sample_html = """
    <html>
    <head><title>Knowledge Test</title></head>
    <body>
        <p>This is a paragraph with enough content to create knowledge items.</p>
        <p>Another paragraph with more test content for chunking.</p>
    </body>
    </html>
    """
    
    test_url = "https://example.com/knowledge-test"
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with patch("src.infrastructure.external.crawler.crawler_client.httpx.AsyncClient") as mock_client:
            mock_robots_response = AsyncMock()
            mock_robots_response.status_code = 404
            
            mock_html_response = AsyncMock()
            mock_html_response.text = sample_html
            mock_html_response.raise_for_status = AsyncMock()
            
            async def mock_get(url, **kwargs):
                if "robots.txt" in url:
                    return mock_robots_response
                return mock_html_response
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            
            response = await ac.post(
                "/api/v1/knowledge/crawl",
                json={
                    "url": test_url,
                    "project_id": str(test_project_id),
                },
                headers=auth_headers,
            )

    assert response.status_code == 202
    document_id = UUID(response.json()["document_id"])

    # Verify knowledge items were created
    pool = await init_pool()
    async with pool.acquire() as conn:
        items = await conn.fetch(
            "SELECT * FROM knowledge_items WHERE document_id = $1", document_id
        )
        assert len(items) > 0, "Should create at least one knowledge item"


async def test_crawl_knowledge_document_type(
    cleanup_knowledge, test_project_id, auth_headers, mock_llm_provider
):
    """Test that crawled documents have type 'web_crawl'."""
    sample_html = "<html><body><p>Type test</p></body></html>"
    test_url = "https://example.com/type-test"
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with patch("src.infrastructure.external.crawler.crawler_client.httpx.AsyncClient") as mock_client:
            mock_robots_response = AsyncMock()
            mock_robots_response.status_code = 404
            
            mock_html_response = AsyncMock()
            mock_html_response.text = sample_html
            mock_html_response.raise_for_status = AsyncMock()
            
            async def mock_get(url, **kwargs):
                if "robots.txt" in url:
                    return mock_robots_response
                return mock_html_response
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            
            response = await ac.post(
                "/api/v1/knowledge/crawl",
                json={
                    "url": test_url,
                    "project_id": str(test_project_id),
                },
                headers=auth_headers,
            )

    assert response.status_code == 202
    document_id = UUID(response.json()["document_id"])

    # Verify document type
    pool = await init_pool()
    async with pool.acquire() as conn:
        doc = await conn.fetchrow("SELECT * FROM documents WHERE id = $1", document_id)
        assert doc["type"] == "web_crawl"
