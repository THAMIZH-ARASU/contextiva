"""PostgreSQL implementation of ITaskRepository.

This module provides the concrete repository implementation for Task entities
using asyncpg and PostgreSQL.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from asyncpg import Pool

from src.domain.models.task import ITaskRepository, Task, TaskPriority, TaskStatus
from src.shared.utils.errors import TaskNotFoundError


class TaskRepository(ITaskRepository):
    """PostgreSQL implementation of task repository."""

    def __init__(self, pool: Pool) -> None:
        """Initialize repository with database connection pool.
        
        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def create(self, task: Task) -> Task:
        """Create a new task in the database.
        
        Args:
            task: Task entity to create
            
        Returns:
            Created task with timestamps populated
        """
        query = """
            INSERT INTO tasks (
                id, project_id, title, description, status, priority,
                assignee, dependencies, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, project_id, title, description, status, priority,
                      assignee, dependencies, created_at, updated_at
        """
        now = datetime.utcnow()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                task.id,
                task.project_id,
                task.title,
                task.description,
                task.status.value,
                task.priority.value,
                task.assignee,
                task.dependencies,
                now,
                now,
            )

        if not row:
            raise RuntimeError("Failed to create task - no row returned")

        return Task(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            priority=TaskPriority(row["priority"]),
            assignee=row["assignee"],
            dependencies=list(row["dependencies"]) if row["dependencies"] else [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_by_id(self, task_id: UUID) -> Optional[Task]:
        """Retrieve a task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task if found, None otherwise
        """
        query = """
            SELECT id, project_id, title, description, status, priority,
                   assignee, dependencies, created_at, updated_at
            FROM tasks
            WHERE id = $1
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, task_id)

        if not row:
            return None

        return Task(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            priority=TaskPriority(row["priority"]),
            assignee=row["assignee"],
            dependencies=list(row["dependencies"]) if row["dependencies"] else [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_by_project(
        self, project_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Task]:
        """Retrieve all tasks for a project.
        
        Args:
            project_id: Project identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of tasks for the project
        """
        query = """
            SELECT id, project_id, title, description, status, priority,
                   assignee, dependencies, created_at, updated_at
            FROM tasks
            WHERE project_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, project_id, limit, skip)

        return [
            Task(
                id=row["id"],
                project_id=row["project_id"],
                title=row["title"],
                description=row["description"],
                status=TaskStatus(row["status"]),
                priority=TaskPriority(row["priority"]),
                assignee=row["assignee"],
                dependencies=list(row["dependencies"]) if row["dependencies"] else [],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    async def get_by_status(
        self, project_id: UUID, status: TaskStatus, skip: int = 0, limit: int = 100
    ) -> list[Task]:
        """Retrieve tasks by status for a project.
        
        Args:
            project_id: Project identifier
            status: Task status to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of tasks with the specified status
        """
        query = """
            SELECT id, project_id, title, description, status, priority,
                   assignee, dependencies, created_at, updated_at
            FROM tasks
            WHERE project_id = $1 AND status = $2
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, project_id, status.value, limit, skip)

        return [
            Task(
                id=row["id"],
                project_id=row["project_id"],
                title=row["title"],
                description=row["description"],
                status=TaskStatus(row["status"]),
                priority=TaskPriority(row["priority"]),
                assignee=row["assignee"],
                dependencies=list(row["dependencies"]) if row["dependencies"] else [],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    async def get_by_assignee(
        self, assignee: str, skip: int = 0, limit: int = 100
    ) -> list[Task]:
        """Retrieve tasks assigned to a specific user.
        
        Args:
            assignee: Assignee identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of tasks assigned to the user
        """
        query = """
            SELECT id, project_id, title, description, status, priority,
                   assignee, dependencies, created_at, updated_at
            FROM tasks
            WHERE assignee = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, assignee, limit, skip)

        return [
            Task(
                id=row["id"],
                project_id=row["project_id"],
                title=row["title"],
                description=row["description"],
                status=TaskStatus(row["status"]),
                priority=TaskPriority(row["priority"]),
                assignee=row["assignee"],
                dependencies=list(row["dependencies"]) if row["dependencies"] else [],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    async def update(self, task: Task) -> Task:
        """Update an existing task.
        
        Args:
            task: Task with updated values
            
        Returns:
            Updated task
            
        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        query = """
            UPDATE tasks
            SET title = $2, description = $3, status = $4, priority = $5,
                assignee = $6, dependencies = $7, updated_at = $8
            WHERE id = $1
            RETURNING id, project_id, title, description, status, priority,
                      assignee, dependencies, created_at, updated_at
        """
        now = datetime.utcnow()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                task.id,
                task.title,
                task.description,
                task.status.value,
                task.priority.value,
                task.assignee,
                task.dependencies,
                now,
            )

        if not row:
            raise TaskNotFoundError(f"Task with id {task.id} not found")

        return Task(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            priority=TaskPriority(row["priority"]),
            assignee=row["assignee"],
            dependencies=list(row["dependencies"]) if row["dependencies"] else [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def delete(self, task_id: UUID) -> bool:
        """Delete a task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if deleted, False if not found
        """
        query = "DELETE FROM tasks WHERE id = $1"

        async with self.pool.acquire() as conn:
            result = await conn.execute(query, task_id)

        # Result is like "DELETE 1" or "DELETE 0"
        return result.endswith("1")
