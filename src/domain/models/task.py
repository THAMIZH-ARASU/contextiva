"""Task domain model and repository interface.

This module defines the Task entity for project task management
with status tracking, priorities, and dependency management.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID


def _utcnow() -> datetime:
    """Helper function to get current UTC datetime."""
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    """Valid task status values."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class TaskPriority(str, Enum):
    """Valid task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(slots=True)
class Task:
    """Task entity representing a project task.
    
    Attributes:
        id: Unique identifier for the task
        project_id: Foreign key to the parent project
        title: Task title (required)
        description: Optional detailed description
        status: Current task status (todo, in_progress, done, blocked)
        priority: Task priority level (low, medium, high, critical)
        assignee: Optional assignee identifier
        dependencies: List of task IDs this task depends on
        created_at: Timestamp when task was created
        updated_at: Timestamp when task was last updated
    """

    id: UUID
    project_id: UUID
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    assignee: Optional[str]
    dependencies: list[UUID] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """Validate task attributes after initialization."""
        # Validate title is not empty
        if not self.title or not self.title.strip():
            raise ValueError("Task title cannot be empty")

        # Ensure status is TaskStatus enum
        if isinstance(self.status, str):
            self.status = TaskStatus(self.status)

        # Ensure priority is TaskPriority enum
        if isinstance(self.priority, str):
            self.priority = TaskPriority(self.priority)

        # Check for circular dependencies (task cannot depend on itself)
        if self.id in self.dependencies:
            raise ValueError(
                f"Circular dependency detected: task {self.id} cannot depend on itself"
            )

        # Detect duplicate dependencies
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("Duplicate dependencies detected")


class ITaskRepository(ABC):
    """Repository interface for Task entity operations."""

    @abstractmethod
    async def create(self, task: Task) -> Task:
        """Create a new task.
        
        Args:
            task: Task entity to create
            
        Returns:
            Created task with generated fields populated
            
        Raises:
            ValueError: If task validation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, task_id: UUID) -> Optional[Task]:
        """Retrieve a task by its ID.
        
        Args:
            task_id: Unique identifier of the task
            
        Returns:
            Task if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_project(
        self, project_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Task]:
        """Retrieve all tasks for a project.
        
        Args:
            project_id: ID of the project
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of tasks belonging to the project
        """
        pass

    @abstractmethod
    async def get_by_status(
        self, project_id: UUID, status: TaskStatus, skip: int = 0, limit: int = 100
    ) -> list[Task]:
        """Retrieve tasks by status for a project.
        
        Args:
            project_id: ID of the project
            status: Task status to filter by
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of tasks with the specified status
        """
        pass

    @abstractmethod
    async def get_by_assignee(
        self, assignee: str, skip: int = 0, limit: int = 100
    ) -> list[Task]:
        """Retrieve tasks assigned to a specific user.
        
        Args:
            assignee: Assignee identifier
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of tasks assigned to the user
        """
        pass

    @abstractmethod
    async def update(self, task: Task) -> Task:
        """Update an existing task.
        
        Args:
            task: Task entity with updated values
            
        Returns:
            Updated task
            
        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        pass

    @abstractmethod
    async def delete(self, task_id: UUID) -> bool:
        """Delete a task by ID.
        
        Args:
            task_id: Unique identifier of the task
            
        Returns:
            True if deleted, False if not found
        """
        pass
