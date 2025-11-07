"""E2E tests for Document Management API endpoints."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

from src.api.main import app
from src.shared.infrastructure.database.connection import init_pool


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def cleanup_documents():
    """Clean up documents table before and after each test."""
    pool = await init_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM documents")
    yield
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM documents")


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
            "Test Project",
            "Active",
        )
    yield project_id
    # Cleanup
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM projects WHERE id = $1", project_id)


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


# ============================================================================
# POST /api/v1/documents - Create Document
# ============================================================================


async def test_create_document_success(
    cleanup_documents, test_project_id, auth_headers
):
    """Test creating a document returns 201 with v1.0.0 version."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/documents",
            json={
                "project_id": str(test_project_id),
                "name": "Architecture Doc",
                "type": "markdown",
                "content_hash": "a" * 64,
            },
            headers=auth_headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Architecture Doc"
    assert data["type"] == "markdown"
    assert data["version"] == "v1.0.0"
    assert data["content_hash"] == "a" * 64
    assert data["project_id"] == str(test_project_id)
    assert "id" in data


async def test_create_document_unauthorized(cleanup_documents, test_project_id):
    """Test creating a document without auth returns 401."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/documents",
            json={
                "project_id": str(test_project_id),
                "name": "Test Doc",
                "type": "pdf",
                "content_hash": "b" * 64,
            },
        )

    assert response.status_code == 401


async def test_create_document_invalid_content_hash(
    cleanup_documents, test_project_id, auth_headers
):
    """Test creating a document with invalid content_hash returns 422."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/documents",
            json={
                "project_id": str(test_project_id),
                "name": "Test Doc",
                "type": "pdf",
                "content_hash": "invalid",  # Not 64 hex chars
            },
            headers=auth_headers,
        )

    assert response.status_code == 422


async def test_create_document_missing_fields(cleanup_documents, auth_headers):
    """Test creating a document with missing required fields returns 422."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/documents",
            json={"name": "Test Doc"},  # Missing project_id, type, content_hash
            headers=auth_headers,
        )

    assert response.status_code == 422


# ============================================================================
# GET /api/v1/documents - List Documents
# ============================================================================


async def test_list_documents_success(
    cleanup_documents, test_project_id, auth_headers
):
    """Test listing documents returns 200 with pagination metadata."""
    # Create 2 test documents
    pool = await init_pool()
    async with pool.acquire() as conn:
        for i in range(2):
            await conn.execute(
                """
                INSERT INTO documents (id, project_id, name, type, version, content_hash)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                uuid4(),
                test_project_id,
                f"Doc {i}",
                "markdown",
                "v1.0.0",
                ("a" + str(i)) * 32,
            )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/documents?project_id={test_project_id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["documents"]) == 2
    assert data["total"] == 2
    assert data["skip"] == 0
    assert data["limit"] == 100


async def test_list_documents_unauthorized(test_project_id):
    """Test listing documents without auth returns 401."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/documents?project_id={test_project_id}",
        )

    assert response.status_code == 401


async def test_list_documents_empty(
    cleanup_documents, test_project_id, auth_headers
):
    """Test listing documents for project with no documents returns empty list."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/documents?project_id={test_project_id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["documents"]) == 0
    assert data["total"] == 0


async def test_list_documents_pagination(
    cleanup_documents, test_project_id, auth_headers
):
    """Test pagination parameters work correctly."""
    # Create 3 documents
    pool = await init_pool()
    async with pool.acquire() as conn:
        for i in range(3):
            await conn.execute(
                """
                INSERT INTO documents (id, project_id, name, type, version, content_hash)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                uuid4(),
                test_project_id,
                f"Doc {i}",
                "markdown",
                "v1.0.0",
                ("a" + str(i)) * 32,
            )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/documents?project_id={test_project_id}&skip=1&limit=1",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["documents"]) == 1
    assert data["skip"] == 1
    assert data["limit"] == 1


async def test_list_documents_max_limit(
    cleanup_documents, test_project_id, auth_headers
):
    """Test max limit enforcement (1000)."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/documents?project_id={test_project_id}&limit=5000",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 1000  # Capped at 1000


# ============================================================================
# GET /api/v1/documents/{id} - Get Document
# ============================================================================


async def test_get_document_success(
    cleanup_documents, test_project_id, auth_headers
):
    """Test retrieving a document returns 200 with correct data."""
    # Create test document
    pool = await init_pool()
    doc_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, name, type, version, content_hash)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            doc_id,
            test_project_id,
            "Test Doc",
            "markdown",
            "v1.0.0",
            "a" * 64,
        )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/documents/{doc_id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(doc_id)
    assert data["name"] == "Test Doc"
    assert data["version"] == "v1.0.0"


async def test_get_document_unauthorized():
    """Test retrieving a document without auth returns 401."""
    doc_id = uuid4()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/documents/{doc_id}")

    assert response.status_code == 401


async def test_get_document_not_found(cleanup_documents, auth_headers):
    """Test retrieving non-existent document returns 404."""
    doc_id = uuid4()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/documents/{doc_id}",
            headers=auth_headers,
        )

    assert response.status_code == 404


# ============================================================================
# PUT /api/v1/documents/{id} - Update Document
# ============================================================================


async def test_update_document_success(
    cleanup_documents, test_project_id, auth_headers
):
    """Test updating document metadata returns 200."""
    # Create test document
    pool = await init_pool()
    doc_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, name, type, version, content_hash)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            doc_id,
            test_project_id,
            "Old Name",
            "markdown",
            "v1.0.0",
            "a" * 64,
        )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.put(
            f"/api/v1/documents/{doc_id}",
            json={"name": "New Name"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["version"] == "v1.0.0"  # Version unchanged


async def test_update_document_unauthorized(test_project_id):
    """Test updating document without auth returns 401."""
    doc_id = uuid4()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.put(
            f"/api/v1/documents/{doc_id}",
            json={"name": "New Name"},
        )

    assert response.status_code == 401


async def test_update_document_not_found(cleanup_documents, auth_headers):
    """Test updating non-existent document returns 404."""
    doc_id = uuid4()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.put(
            f"/api/v1/documents/{doc_id}",
            json={"name": "New Name"},
            headers=auth_headers,
        )

    assert response.status_code == 404


async def test_update_document_partial(
    cleanup_documents, test_project_id, auth_headers
):
    """Test partial update changes only specified fields."""
    # Create test document
    pool = await init_pool()
    doc_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, name, type, version, content_hash)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            doc_id,
            test_project_id,
            "Original Name",
            "markdown",
            "v1.0.0",
            "a" * 64,
        )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.put(
            f"/api/v1/documents/{doc_id}",
            json={"name": "Updated Name"},  # Only updating name
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["content_hash"] == "a" * 64  # Unchanged


async def test_update_document_invalid_name(
    cleanup_documents, test_project_id, auth_headers
):
    """Test updating with invalid name returns 422."""
    # Create test document
    pool = await init_pool()
    doc_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, name, type, version, content_hash)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            doc_id,
            test_project_id,
            "Test Doc",
            "markdown",
            "v1.0.0",
            "a" * 64,
        )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.put(
            f"/api/v1/documents/{doc_id}",
            json={"name": ""},  # Empty name
            headers=auth_headers,
        )

    assert response.status_code == 422


# ============================================================================
# DELETE /api/v1/documents/{id} - Delete Document
# ============================================================================


async def test_delete_document_success(
    cleanup_documents, test_project_id, auth_headers
):
    """Test deleting document returns 204."""
    # Create test document
    pool = await init_pool()
    doc_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, name, type, version, content_hash)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            doc_id,
            test_project_id,
            "Test Doc",
            "markdown",
            "v1.0.0",
            "a" * 64,
        )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete(
            f"/api/v1/documents/{doc_id}",
            headers=auth_headers,
        )

    assert response.status_code == 204


async def test_delete_document_unauthorized():
    """Test deleting document without auth returns 401."""
    doc_id = uuid4()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete(f"/api/v1/documents/{doc_id}")

    assert response.status_code == 401


async def test_delete_document_not_found(cleanup_documents, auth_headers):
    """Test deleting non-existent document returns 404."""
    doc_id = uuid4()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete(
            f"/api/v1/documents/{doc_id}",
            headers=auth_headers,
        )

    assert response.status_code == 404


# ============================================================================
# POST /api/v1/documents/{id}/version - Create Document Version
# ============================================================================


async def test_create_version_major(
    cleanup_documents, test_project_id, auth_headers
):
    """Test creating major version bump (v1.2.3 → v2.0.0)."""
    # Create test document
    pool = await init_pool()
    doc_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, name, type, version, content_hash)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            doc_id,
            test_project_id,
            "Test Doc",
            "markdown",
            "v1.2.3",
            "a" * 64,
        )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/documents/{doc_id}/version",
            json={"content_hash": "b" * 64, "bump_type": "major"},
            headers=auth_headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["version"] == "v2.0.0"
    assert data["content_hash"] == "b" * 64
    assert data["name"] == "Test Doc"  # Same name
    assert data["id"] != str(doc_id)  # New ID


async def test_create_version_minor(
    cleanup_documents, test_project_id, auth_headers
):
    """Test creating minor version bump (v1.2.3 → v1.3.0)."""
    # Create test document
    pool = await init_pool()
    doc_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, name, type, version, content_hash)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            doc_id,
            test_project_id,
            "Test Doc",
            "markdown",
            "v1.2.3",
            "a" * 64,
        )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/documents/{doc_id}/version",
            json={"content_hash": "c" * 64, "bump_type": "minor"},
            headers=auth_headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["version"] == "v1.3.0"


async def test_create_version_patch(
    cleanup_documents, test_project_id, auth_headers
):
    """Test creating patch version bump (v1.2.3 → v1.2.4)."""
    # Create test document
    pool = await init_pool()
    doc_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, name, type, version, content_hash)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            doc_id,
            test_project_id,
            "Test Doc",
            "markdown",
            "v1.2.3",
            "a" * 64,
        )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/documents/{doc_id}/version",
            json={"content_hash": "d" * 64, "bump_type": "patch"},
            headers=auth_headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["version"] == "v1.2.4"


async def test_create_version_unauthorized():
    """Test creating version without auth returns 401."""
    doc_id = uuid4()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/documents/{doc_id}/version",
            json={"content_hash": "e" * 64, "bump_type": "minor"},
        )

    assert response.status_code == 401


async def test_create_version_not_found(cleanup_documents, auth_headers):
    """Test creating version for non-existent document returns 404."""
    doc_id = uuid4()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/documents/{doc_id}/version",
            json={"content_hash": "f" * 64, "bump_type": "minor"},
            headers=auth_headers,
        )

    assert response.status_code == 404


async def test_create_version_invalid_content_hash(
    cleanup_documents, test_project_id, auth_headers
):
    """Test creating version with invalid content_hash returns 422."""
    # Create test document
    pool = await init_pool()
    doc_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, name, type, version, content_hash)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            doc_id,
            test_project_id,
            "Test Doc",
            "markdown",
            "v1.0.0",
            "a" * 64,
        )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/documents/{doc_id}/version",
            json={"content_hash": "invalid", "bump_type": "minor"},
            headers=auth_headers,
        )

    assert response.status_code == 422
