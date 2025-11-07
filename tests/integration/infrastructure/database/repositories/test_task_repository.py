"""Integration tests for TaskRepository."""

import pytest
import asyncpg
from uuid import uuid4

from src.domain.models.task import Task, TaskStatus, TaskPriority
from src.infrastructure.database.repositories.task_repository import TaskRepository
from src.shared.config.settings import load_settings
from src.shared.utils.errors import TaskNotFoundError


async def get_fresh_pool():
    """Create a fresh connection pool for each test (bypass singleton)."""
    settings = load_settings()
    return await asyncpg.create_pool(dsn=settings.db.dsn, min_size=1, max_size=5)


async def create_test_project():
    """Helper to create a test project and return pool + project_id."""
    pool = await get_fresh_pool()
    project_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO projects (id, name, description, status, tags, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
            """,
            project_id,
            "Test Project",
            "Integration test project",
            "Active",
            [],
        )
    return pool, project_id


async def cleanup_test_project(pool, project_id):
    """Cleanup test project (CASCADE delete) and close pool."""
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM projects WHERE id = $1", project_id)
    await pool.close()


@pytest.mark.asyncio
class TestTaskRepository:
    """Integration tests for TaskRepository."""

    async def test_create_task(self):
        """Test creating a task in the database."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)
        task = Task(
            id=uuid4(),
            project_id=project_id,
            title="Implement feature X",
            description="Add new feature",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee="user@example.com",
            dependencies=[],
        )

        try:
            # Act
            created = await repo.create(task)

            # Assert
            assert created.id == task.id
            assert created.project_id == project_id
            assert created.title == "Implement feature X"
            assert created.status == TaskStatus.TODO
            assert created.priority == TaskPriority.HIGH
            assert created.assignee == "user@example.com"
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_create_task_with_dependencies(self):
        """Test creating a task with dependencies."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)
        
        # Create dependency task first
        dep_task = Task(
            id=uuid4(),
            project_id=project_id,
            title="Dependency task",
            description=None,
            status=TaskStatus.DONE,
            priority=TaskPriority.LOW,
            assignee=None,
            dependencies=[],
        )
        await repo.create(dep_task)

        # Create task with dependency
        task = Task(
            id=uuid4(),
            project_id=project_id,
            title="Main task",
            description=None,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee=None,
            dependencies=[dep_task.id],
        )

        try:
            # Act
            created = await repo.create(task)

            # Assert
            assert len(created.dependencies) == 1
            assert dep_task.id in created.dependencies
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_get_by_id_existing(self):
        """Test retrieving an existing task by ID."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)
        task = Task(
            id=uuid4(),
            project_id=project_id,
            title="Test task",
            description="Description",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.CRITICAL,
            assignee="dev@example.com",
            dependencies=[],
        )
        await repo.create(task)

        try:
            # Act
            found = await repo.get_by_id(task.id)

            # Assert
            assert found is not None
            assert found.id == task.id
            assert found.title == "Test task"
            assert found.status == TaskStatus.IN_PROGRESS
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_get_by_id_nonexistent(self):
        """Test retrieving a non-existent task returns None."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)

        try:
            # Act
            found = await repo.get_by_id(uuid4())

            # Assert
            assert found is None
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_get_by_project(self):
        """Test retrieving all tasks for a project."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)
        task1 = Task(
            id=uuid4(),
            project_id=project_id,
            title="Task 1",
            description=None,
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee=None,
            dependencies=[],
        )
        task2 = Task(
            id=uuid4(),
            project_id=project_id,
            title="Task 2",
            description=None,
            status=TaskStatus.DONE,
            priority=TaskPriority.HIGH,
            assignee=None,
            dependencies=[],
        )
        await repo.create(task1)
        await repo.create(task2)

        try:
            # Act
            tasks = await repo.get_by_project(project_id)

            # Assert
            assert len(tasks) == 2
            task_ids = [t.id for t in tasks]
            assert task1.id in task_ids
            assert task2.id in task_ids
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_get_by_status(self):
        """Test retrieving tasks by status."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)
        task_todo = Task(
            id=uuid4(),
            project_id=project_id,
            title="TODO task",
            description=None,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee=None,
            dependencies=[],
        )
        task_done = Task(
            id=uuid4(),
            project_id=project_id,
            title="DONE task",
            description=None,
            status=TaskStatus.DONE,
            priority=TaskPriority.MEDIUM,
            assignee=None,
            dependencies=[],
        )
        await repo.create(task_todo)
        await repo.create(task_done)

        try:
            # Act
            todo_tasks = await repo.get_by_status(project_id, TaskStatus.TODO)

            # Assert
            assert len(todo_tasks) == 1
            assert todo_tasks[0].id == task_todo.id
            assert todo_tasks[0].status == TaskStatus.TODO
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_get_by_assignee(self):
        """Test retrieving tasks by assignee."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)
        assignee_email = "developer@example.com"
        
        task1 = Task(
            id=uuid4(),
            project_id=project_id,
            title="Assigned task 1",
            description=None,
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee=assignee_email,
            dependencies=[],
        )
        task2 = Task(
            id=uuid4(),
            project_id=project_id,
            title="Assigned task 2",
            description=None,
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            assignee=assignee_email,
            dependencies=[],
        )
        task_other = Task(
            id=uuid4(),
            project_id=project_id,
            title="Other task",
            description=None,
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee="other@example.com",
            dependencies=[],
        )
        await repo.create(task1)
        await repo.create(task2)
        await repo.create(task_other)

        try:
            # Act
            assigned_tasks = await repo.get_by_assignee(assignee_email)

            # Assert
            assert len(assigned_tasks) == 2
            for task in assigned_tasks:
                assert task.assignee == assignee_email
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_update_task(self):
        """Test updating an existing task."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)
        task = Task(
            id=uuid4(),
            project_id=project_id,
            title="Original title",
            description="Original description",
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee=None,
            dependencies=[],
        )
        created = await repo.create(task)

        try:
            # Act
            created.title = "Updated title"
            created.status = TaskStatus.IN_PROGRESS
            created.priority = TaskPriority.CRITICAL
            created.assignee = "dev@example.com"
            updated = await repo.update(created)

            # Assert
            assert updated.title == "Updated title"
            assert updated.status == TaskStatus.IN_PROGRESS
            assert updated.priority == TaskPriority.CRITICAL
            assert updated.assignee == "dev@example.com"
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_update_task_dependencies(self):
        """Test updating task dependencies."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)
        dep1 = uuid4()
        dep2 = uuid4()
        
        task = Task(
            id=uuid4(),
            project_id=project_id,
            title="Task",
            description=None,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee=None,
            dependencies=[],
        )
        created = await repo.create(task)

        try:
            # Act
            created.dependencies = [dep1, dep2]
            updated = await repo.update(created)

            # Assert
            assert len(updated.dependencies) == 2
            assert dep1 in updated.dependencies
            assert dep2 in updated.dependencies
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_update_nonexistent_raises_error(self):
        """Test updating non-existent task raises error."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)
        task = Task(
            id=uuid4(),
            project_id=uuid4(),
            title="Ghost task",
            description=None,
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee=None,
            dependencies=[],
        )

        try:
            # Act & Assert
            with pytest.raises(TaskNotFoundError):
                await repo.update(task)
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_delete_task(self):
        """Test deleting a task."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)
        task = Task(
            id=uuid4(),
            project_id=project_id,
            title="Delete me",
            description=None,
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee=None,
            dependencies=[],
        )
        await repo.create(task)

        try:
            # Act
            deleted = await repo.delete(task.id)

            # Assert
            assert deleted is True
            found = await repo.get_by_id(task.id)
            assert found is None
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_delete_nonexistent_returns_false(self):
        """Test deleting non-existent task returns False."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)

        try:
            # Act
            deleted = await repo.delete(uuid4())

            # Assert
            assert deleted is False
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_all_task_statuses(self):
        """Test creating tasks with all possible statuses."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)
        statuses = [
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.DONE,
            TaskStatus.BLOCKED,
        ]

        try:
            # Act & Assert
            for status in statuses:
                task = Task(
                    id=uuid4(),
                    project_id=project_id,
                    title=f"Task {status.value}",
                    description=None,
                    status=status,
                    priority=TaskPriority.MEDIUM,
                    assignee=None,
                    dependencies=[],
                )
                created = await repo.create(task)
                assert created.status == status
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_all_task_priorities(self):
        """Test creating tasks with all possible priorities."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)
        priorities = [
            TaskPriority.LOW,
            TaskPriority.MEDIUM,
            TaskPriority.HIGH,
            TaskPriority.CRITICAL,
        ]

        try:
            # Act & Assert
            for priority in priorities:
                task = Task(
                    id=uuid4(),
                    project_id=project_id,
                    title=f"Task {priority.value}",
                    description=None,
                    status=TaskStatus.TODO,
                    priority=priority,
                    assignee=None,
                    dependencies=[],
                )
                created = await repo.create(task)
                assert created.priority == priority
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_pagination(self):
        """Test pagination with skip and limit."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = TaskRepository(pool)
        
        # Create 5 tasks
        for i in range(5):
            task = Task(
                id=uuid4(),
                project_id=project_id,
                title=f"Task {i}",
                description=None,
                status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                assignee=None,
                dependencies=[],
            )
            await repo.create(task)

        try:
            # Act
            page1 = await repo.get_by_project(project_id, skip=0, limit=2)
            page2 = await repo.get_by_project(project_id, skip=2, limit=2)

            # Assert
            assert len(page1) == 2
            assert len(page2) == 2
            # Ensure no overlap
            page1_ids = {t.id for t in page1}
            page2_ids = {t.id for t in page2}
            assert page1_ids.isdisjoint(page2_ids)
        finally:
            await cleanup_test_project(pool, project_id)
