import pytest
import pytest_asyncio

from src.domain.models.project import Project
from src.infrastructure.database.repositories.project_repository import ProjectRepository
from src.shared.infrastructure.database.connection import init_pool


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def _isolate_db():
    """Ensure test isolation by cleaning projects table before each test."""
    try:
        pool = await init_pool()
    except Exception as e:
        pytest.skip(f"Postgres not available for integration tests: {e}")
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM projects")
    yield


async def test_crud_project_repository():
    repo = ProjectRepository()

    # Create
    p = Project(name="RepoTest", description="desc", tags=["t1"]) 
    created = await repo.create(p)
    assert created.id == p.id

    # Get by id
    fetched = await repo.get_by_id(p.id)
    assert fetched is not None
    assert fetched.name == "RepoTest"

    # Get all
    items = await repo.get_all(limit=10, offset=0)
    assert any(it.id == p.id for it in items)

    # Update
    p.name = "RepoTest2"
    updated = await repo.update(p)
    assert updated.name == "RepoTest2"

    # Delete
    await repo.delete(p.id)
    missing = await repo.get_by_id(p.id)
    assert missing is None