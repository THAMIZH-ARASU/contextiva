"""E2E tests for Task Management API endpoints."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.shared.infrastructure.database.connection import init_pool

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def cleanup_tasks():
    """Clean up tasks table before and after each test."""
    pool = await init_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM tasks")
    yield
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM tasks")


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
# POST /api/v1/tasks - Create Task
# ============================================================================


async def test_create_task_success(cleanup_tasks, test_project_id, auth_headers):
    """Test creating a task returns 201 with all fields."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/tasks",
            json={
                "project_id": str(test_project_id),
                "title": "Implement authentication",
                "description": "Add JWT-based auth",
                "status": "todo",
                "priority": "high",
                "assignee": "dev-001",
                "dependencies": [],
            },
            headers=auth_headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Implement authentication"
    assert data["description"] == "Add JWT-based auth"
    assert data["status"] == "todo"
    assert data["priority"] == "high"
    assert data["assignee"] == "dev-001"
    assert data["dependencies"] == []
    assert data["project_id"] == str(test_project_id)
    assert "id" in data


async def test_create_task_with_defaults(cleanup_tasks, test_project_id, auth_headers):
    """Test creating a task with default status and priority."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/tasks",
            json={
                "project_id": str(test_project_id),
                "title": "Simple task",
            },
            headers=auth_headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "todo"  # Default
    assert data["priority"] == "medium"  # Default
    assert data["dependencies"] == []


async def test_create_task_unauthorized(cleanup_tasks, test_project_id):
    """Test creating a task without auth returns 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/tasks",
            json={
                "project_id": str(test_project_id),
                "title": "Test Task",
            },
        )

    assert response.status_code == 401


async def test_create_task_empty_title(cleanup_tasks, test_project_id, auth_headers):
    """Test creating a task with empty title returns 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/tasks",
            json={
                "project_id": str(test_project_id),
                "title": "",  # Empty title
            },
            headers=auth_headers,
        )

    assert response.status_code == 422


async def test_create_task_invalid_status(cleanup_tasks, test_project_id, auth_headers):
    """Test creating a task with invalid status returns 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/tasks",
            json={
                "project_id": str(test_project_id),
                "title": "Test Task",
                "status": "invalid_status",
            },
            headers=auth_headers,
        )

    assert response.status_code == 422


async def test_create_task_duplicate_dependencies(
    cleanup_tasks, test_project_id, auth_headers
):
    """Test creating a task with duplicate dependencies returns 422."""
    dep_id = str(uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/tasks",
            json={
                "project_id": str(test_project_id),
                "title": "Test Task",
                "dependencies": [dep_id, dep_id],  # Duplicate
            },
            headers=auth_headers,
        )

    assert response.status_code == 422


# ============================================================================
# GET /api/v1/tasks - List Tasks
# ============================================================================


async def test_list_tasks_success(cleanup_tasks, test_project_id, auth_headers):
    """Test listing tasks returns 200 with pagination metadata."""
    # Create test tasks
    pool = await init_pool()
    task_id1 = uuid4()
    task_id2 = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, status, priority)
            VALUES ($1, $2, $3, $4, $5), ($6, $7, $8, $9, $10)
            """,
            task_id1,
            test_project_id,
            "Task 1",
            "todo",
            "medium",
            task_id2,
            test_project_id,
            "Task 2",
            "in_progress",
            "high",
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/api/v1/tasks?project_id={test_project_id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 2
    assert data["total"] >= 2
    assert data["skip"] == 0
    assert data["limit"] == 100


async def test_list_tasks_empty(cleanup_tasks, test_project_id, auth_headers):
    """Test listing tasks when none exist returns empty list."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/api/v1/tasks?project_id={test_project_id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["tasks"] == []
    assert data["total"] == 0


async def test_list_tasks_filter_by_status(
    cleanup_tasks, test_project_id, auth_headers
):
    """Test filtering tasks by status returns only matching tasks."""
    # Create test tasks with different statuses
    pool = await init_pool()
    task_id1 = uuid4()
    task_id2 = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, status, priority)
            VALUES ($1, $2, $3, $4, $5), ($6, $7, $8, $9, $10)
            """,
            task_id1,
            test_project_id,
            "Task 1",
            "todo",
            "medium",
            task_id2,
            test_project_id,
            "Task 2",
            "done",
            "high",
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/api/v1/tasks?project_id={test_project_id}&status_filter=done",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["status"] == "done"


async def test_list_tasks_filter_by_assignee(
    cleanup_tasks, test_project_id, auth_headers
):
    """Test filtering tasks by assignee returns only matching tasks."""
    # Create test tasks with different assignees
    pool = await init_pool()
    task_id1 = uuid4()
    task_id2 = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, status, priority, assignee)
            VALUES ($1, $2, $3, $4, $5, $6), ($7, $8, $9, $10, $11, $12)
            """,
            task_id1,
            test_project_id,
            "Task 1",
            "todo",
            "medium",
            "dev-001",
            task_id2,
            test_project_id,
            "Task 2",
            "todo",
            "high",
            "dev-002",
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/api/v1/tasks?project_id={test_project_id}&assignee=dev-001",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["assignee"] == "dev-001"


async def test_list_tasks_pagination(cleanup_tasks, test_project_id, auth_headers):
    """Test pagination with skip and limit parameters."""
    # Create 5 test tasks
    pool = await init_pool()
    async with pool.acquire() as conn:
        for i in range(5):
            await conn.execute(
                """
                INSERT INTO tasks (id, project_id, title, status, priority)
                VALUES ($1, $2, $3, $4, $5)
                """,
                uuid4(),
                test_project_id,
                f"Task {i}",
                "todo",
                "medium",
            )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/api/v1/tasks?project_id={test_project_id}&skip=2&limit=2",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 2
    assert data["skip"] == 2
    assert data["limit"] == 2


async def test_list_tasks_max_limit_enforcement(
    cleanup_tasks, test_project_id, auth_headers
):
    """Test that limit is capped at 1000."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/api/v1/tasks?project_id={test_project_id}&limit=9999",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 1000  # Capped at max


# ============================================================================
# GET /api/v1/tasks/{id} - Get Single Task
# ============================================================================


async def test_get_task_success(cleanup_tasks, test_project_id, auth_headers):
    """Test retrieving a single task returns 200."""
    # Create test task
    pool = await init_pool()
    task_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, status, priority, dependencies)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            task_id,
            test_project_id,
            "Test Task",
            "todo",
            "high",
            [],
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/api/v1/tasks/{task_id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(task_id)
    assert data["title"] == "Test Task"
    assert data["dependencies"] == []


async def test_get_task_not_found(cleanup_tasks, auth_headers):
    """Test retrieving non-existent task returns 404."""
    fake_id = uuid4()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/api/v1/tasks/{fake_id}",
            headers=auth_headers,
        )

    assert response.status_code == 404


async def test_get_task_unauthorized(cleanup_tasks, test_project_id):
    """Test retrieving a task without auth returns 401."""
    task_id = uuid4()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 401


# ============================================================================
# PUT /api/v1/tasks/{id} - Update Task
# ============================================================================


async def test_update_task_success(cleanup_tasks, test_project_id, auth_headers):
    """Test updating a task returns 200 with updated fields."""
    # Create test task
    pool = await init_pool()
    task_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, status, priority)
            VALUES ($1, $2, $3, $4, $5)
            """,
            task_id,
            test_project_id,
            "Original Title",
            "todo",
            "medium",
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.put(
            f"/api/v1/tasks/{task_id}",
            json={
                "title": "Updated Title",
                "status": "in_progress",
                "priority": "high",
            },
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "in_progress"
    assert data["priority"] == "high"


async def test_update_task_partial(cleanup_tasks, test_project_id, auth_headers):
    """Test partial update only changes specified fields."""
    # Create test task
    pool = await init_pool()
    task_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, status, priority)
            VALUES ($1, $2, $3, $4, $5)
            """,
            task_id,
            test_project_id,
            "Original Title",
            "todo",
            "medium",
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.put(
            f"/api/v1/tasks/{task_id}",
            json={"status": "done"},  # Only update status
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Original Title"  # Unchanged
    assert data["status"] == "done"  # Updated
    assert data["priority"] == "medium"  # Unchanged


async def test_update_task_circular_dependency(
    cleanup_tasks, test_project_id, auth_headers
):
    """Test updating task with circular dependency returns 422."""
    # Create test task
    pool = await init_pool()
    task_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, status, priority)
            VALUES ($1, $2, $3, $4, $5)
            """,
            task_id,
            test_project_id,
            "Test Task",
            "todo",
            "medium",
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.put(
            f"/api/v1/tasks/{task_id}",
            json={"dependencies": [str(task_id)]},  # Self-dependency
            headers=auth_headers,
        )

    assert response.status_code == 422


async def test_update_task_not_found(cleanup_tasks, auth_headers):
    """Test updating non-existent task returns 404."""
    fake_id = uuid4()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.put(
            f"/api/v1/tasks/{fake_id}",
            json={"status": "done"},
            headers=auth_headers,
        )

    assert response.status_code == 404


# ============================================================================
# DELETE /api/v1/tasks/{id} - Delete Task
# ============================================================================


async def test_delete_task_success(cleanup_tasks, test_project_id, auth_headers):
    """Test deleting a task returns 204."""
    # Create test task
    pool = await init_pool()
    task_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, status, priority)
            VALUES ($1, $2, $3, $4, $5)
            """,
            task_id,
            test_project_id,
            "Test Task",
            "todo",
            "medium",
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.delete(
            f"/api/v1/tasks/{task_id}",
            headers=auth_headers,
        )

    assert response.status_code == 204


async def test_delete_task_verify_deleted(
    cleanup_tasks, test_project_id, auth_headers
):
    """Test that deleted task cannot be retrieved."""
    # Create test task
    pool = await init_pool()
    task_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, status, priority)
            VALUES ($1, $2, $3, $4, $5)
            """,
            task_id,
            test_project_id,
            "Test Task",
            "todo",
            "medium",
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Delete the task
        delete_response = await ac.delete(
            f"/api/v1/tasks/{task_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        # Verify it's gone
        get_response = await ac.get(
            f"/api/v1/tasks/{task_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404


async def test_delete_task_not_found(cleanup_tasks, auth_headers):
    """Test deleting non-existent task returns 404."""
    fake_id = uuid4()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.delete(
            f"/api/v1/tasks/{fake_id}",
            headers=auth_headers,
        )

    assert response.status_code == 404


async def test_delete_task_unauthorized(cleanup_tasks, test_project_id):
    """Test deleting a task without auth returns 401."""
    task_id = uuid4()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.delete(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 401
