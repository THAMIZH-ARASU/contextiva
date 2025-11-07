"""E2E tests for Project Management API endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4

from src.api.main import app
from src.shared.infrastructure.database.connection import init_pool


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def cleanup_projects():
    """Clean up projects table before and after each test."""
    pool = await init_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM projects")
    yield
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM projects")


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
# POST /api/v1/projects - Create Project
# ============================================================================


async def test_create_project_success(cleanup_projects, auth_headers):
    """Test creating a project with valid data returns 201 and project with ID."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/projects",
            json={
                "name": "Test Project",
                "description": "A test project",
                "tags": ["test", "ai"],
            },
            headers=auth_headers,
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["description"] == "A test project"
    assert data["status"] == "Active"
    assert data["tags"] == ["test", "ai"]
    assert "id" in data


async def test_create_project_minimal(cleanup_projects, auth_headers):
    """Test creating a project with only required fields."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/projects",
            json={"name": "Minimal Project"},
            headers=auth_headers,
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Project"
    assert data["description"] is None
    assert data["tags"] is None
    assert data["status"] == "Active"


async def test_create_project_invalid_name_empty(cleanup_projects, auth_headers):
    """Test creating a project with empty name returns 422."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/projects",
            json={"name": ""},
            headers=auth_headers,
        )
    
    assert response.status_code == 422


async def test_create_project_invalid_name_whitespace(cleanup_projects, auth_headers):
    """Test creating a project with whitespace-only name returns 422."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/projects",
            json={"name": "   "},
            headers=auth_headers,
        )
    
    assert response.status_code == 422


async def test_create_project_invalid_tags(cleanup_projects, auth_headers):
    """Test creating a project with invalid tag format returns 422."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/projects",
            json={"name": "Test", "tags": ["invalid tag with spaces"]},
            headers=auth_headers,
        )
    
    assert response.status_code == 422


async def test_create_project_missing_name(cleanup_projects, auth_headers):
    """Test creating a project without name returns 422."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/projects",
            json={"description": "Missing name"},
            headers=auth_headers,
        )
    
    assert response.status_code == 422


async def test_create_project_unauthorized(cleanup_projects):
    """Test creating a project without authentication returns 401."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/projects",
            json={"name": "Test Project"},
        )
    
    assert response.status_code == 401


# ============================================================================
# GET /api/v1/projects - List Projects
# ============================================================================


async def test_list_projects_empty(cleanup_projects, auth_headers):
    """Test listing projects when none exist returns empty list."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/projects", headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json() == []


async def test_list_projects_with_data(cleanup_projects, auth_headers):
    """Test listing projects returns all created projects."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Create two projects
        await ac.post(
            "/api/v1/projects",
            json={"name": "Project 1"},
            headers=auth_headers,
        )
        await ac.post(
            "/api/v1/projects",
            json={"name": "Project 2"},
            headers=auth_headers,
        )
        
        # List projects
        response = await ac.get("/api/v1/projects", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(p["name"] == "Project 1" for p in data)
    assert any(p["name"] == "Project 2" for p in data)


async def test_list_projects_pagination(cleanup_projects, auth_headers):
    """Test listing projects with pagination parameters."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Create 5 projects
        for i in range(5):
            await ac.post(
                "/api/v1/projects",
                json={"name": f"Project {i}"},
                headers=auth_headers,
            )
        
        # Get first 2 projects
        response = await ac.get(
            "/api/v1/projects?limit=2&skip=0",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 2
        
        # Get next 2 projects
        response = await ac.get(
            "/api/v1/projects?limit=2&skip=2",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 2


async def test_list_projects_unauthorized(cleanup_projects):
    """Test listing projects without authentication returns 401."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/projects")
    
    assert response.status_code == 401


# ============================================================================
# GET /api/v1/projects/{id} - Get Project by ID
# ============================================================================


async def test_get_project_success(cleanup_projects, auth_headers):
    """Test getting a project by ID returns the correct project."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Create project
        create_response = await ac.post(
            "/api/v1/projects",
            json={"name": "Get Me", "description": "Find me"},
            headers=auth_headers,
        )
        project_id = create_response.json()["id"]
        
        # Get project by ID
        response = await ac.get(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == "Get Me"
    assert data["description"] == "Find me"


async def test_get_project_not_found(cleanup_projects, auth_headers):
    """Test getting a non-existent project returns 404."""
    random_uuid = str(uuid4())
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/projects/{random_uuid}",
            headers=auth_headers,
        )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_get_project_invalid_uuid(cleanup_projects, auth_headers):
    """Test getting a project with invalid UUID format returns 422."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/projects/invalid-uuid",
            headers=auth_headers,
        )
    
    assert response.status_code == 422


async def test_get_project_unauthorized(cleanup_projects):
    """Test getting a project without authentication returns 401."""
    random_uuid = str(uuid4())
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/projects/{random_uuid}")
    
    assert response.status_code == 401


# ============================================================================
# PUT /api/v1/projects/{id} - Update Project
# ============================================================================


async def test_update_project_success(cleanup_projects, auth_headers):
    """Test updating a project with valid data returns updated project."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Create project
        create_response = await ac.post(
            "/api/v1/projects",
            json={"name": "Original", "description": "Original desc"},
            headers=auth_headers,
        )
        project_id = create_response.json()["id"]
        
        # Update project
        response = await ac.put(
            f"/api/v1/projects/{project_id}",
            json={"name": "Updated", "status": "Archived"},
            headers=auth_headers,
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["description"] == "Original desc"  # Not updated
    assert data["status"] == "Archived"


async def test_update_project_partial(cleanup_projects, auth_headers):
    """Test updating only some fields keeps others unchanged."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Create project
        create_response = await ac.post(
            "/api/v1/projects",
            json={"name": "Original", "tags": ["tag1"]},
            headers=auth_headers,
        )
        project_id = create_response.json()["id"]
        
        # Update only description
        response = await ac.put(
            f"/api/v1/projects/{project_id}",
            json={"description": "New description"},
            headers=auth_headers,
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Original"  # Unchanged
    assert data["description"] == "New description"
    assert data["tags"] == ["tag1"]  # Unchanged


async def test_update_project_not_found(cleanup_projects, auth_headers):
    """Test updating a non-existent project returns 404."""
    random_uuid = str(uuid4())
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.put(
            f"/api/v1/projects/{random_uuid}",
            json={"name": "Updated"},
            headers=auth_headers,
        )
    
    assert response.status_code == 404


async def test_update_project_invalid_status(cleanup_projects, auth_headers):
    """Test updating with invalid status returns 422."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Create project
        create_response = await ac.post(
            "/api/v1/projects",
            json={"name": "Test"},
            headers=auth_headers,
        )
        project_id = create_response.json()["id"]
        
        # Update with invalid status
        response = await ac.put(
            f"/api/v1/projects/{project_id}",
            json={"status": "InvalidStatus"},
            headers=auth_headers,
        )
    
    assert response.status_code == 422


async def test_update_project_unauthorized(cleanup_projects):
    """Test updating a project without authentication returns 401."""
    random_uuid = str(uuid4())
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.put(
            f"/api/v1/projects/{random_uuid}",
            json={"name": "Updated"},
        )
    
    assert response.status_code == 401


# ============================================================================
# DELETE /api/v1/projects/{id} - Delete Project
# ============================================================================


async def test_delete_project_success(cleanup_projects, auth_headers):
    """Test deleting a project returns 204 and removes it from database."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Create project
        create_response = await ac.post(
            "/api/v1/projects",
            json={"name": "Delete Me"},
            headers=auth_headers,
        )
        project_id = create_response.json()["id"]
        
        # Delete project
        response = await ac.delete(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = await ac.get(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404


async def test_delete_project_not_found(cleanup_projects, auth_headers):
    """Test deleting a non-existent project returns 404."""
    random_uuid = str(uuid4())
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete(
            f"/api/v1/projects/{random_uuid}",
            headers=auth_headers,
        )
    
    assert response.status_code == 404


async def test_delete_project_unauthorized(cleanup_projects):
    """Test deleting a project without authentication returns 401."""
    random_uuid = str(uuid4())
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete(f"/api/v1/projects/{random_uuid}")
    
    assert response.status_code == 401
