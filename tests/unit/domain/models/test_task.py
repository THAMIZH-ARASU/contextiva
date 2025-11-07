"""Unit tests for Task domain model."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.models.task import Task, TaskStatus, TaskPriority


class TestTask:
    """Test suite for Task entity."""

    def test_create_valid_task(self):
        """Test creating a valid task."""
        # Arrange
        task_id = uuid4()
        project_id = uuid4()

        # Act
        task = Task(
            id=task_id,
            project_id=project_id,
            title="Implement feature X",
            description="Add new feature",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee="user@example.com",
            dependencies=[],
        )

        # Assert
        assert task.id == task_id
        assert task.project_id == project_id
        assert task.title == "Implement feature X"
        assert task.description == "Add new feature"
        assert task.status == TaskStatus.TODO
        assert task.priority == TaskPriority.HIGH
        assert task.assignee == "user@example.com"
        assert task.dependencies == []

    def test_task_with_string_enums_converts(self):
        """Test that string status/priority are converted to enums."""
        # Act
        task = Task(
            id=uuid4(),
            project_id=uuid4(),
            title="Task",
            description=None,
            status="in_progress",  # String
            priority="critical",  # String
            assignee=None,
            dependencies=[],
        )

        # Assert
        assert task.status == TaskStatus.IN_PROGRESS
        assert isinstance(task.status, TaskStatus)
        assert task.priority == TaskPriority.CRITICAL
        assert isinstance(task.priority, TaskPriority)

    def test_empty_title_raises_error(self):
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            Task(
                id=uuid4(),
                project_id=uuid4(),
                title="",
                description=None,
                status=TaskStatus.TODO,
                priority=TaskPriority.LOW,
                assignee=None,
                dependencies=[],
            )

    def test_whitespace_only_title_raises_error(self):
        """Test that whitespace-only title raises ValueError."""
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            Task(
                id=uuid4(),
                project_id=uuid4(),
                title="   ",
                description=None,
                status=TaskStatus.TODO,
                priority=TaskPriority.LOW,
                assignee=None,
                dependencies=[],
            )

    def test_all_task_statuses(self):
        """Test all valid task statuses."""
        statuses = [
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.DONE,
            TaskStatus.BLOCKED,
        ]

        for status in statuses:
            task = Task(
                id=uuid4(),
                project_id=uuid4(),
                title="Test Task",
                description=None,
                status=status,
                priority=TaskPriority.MEDIUM,
                assignee=None,
                dependencies=[],
            )
            assert task.status == status

    def test_all_task_priorities(self):
        """Test all valid task priorities."""
        priorities = [
            TaskPriority.LOW,
            TaskPriority.MEDIUM,
            TaskPriority.HIGH,
            TaskPriority.CRITICAL,
        ]

        for priority in priorities:
            task = Task(
                id=uuid4(),
                project_id=uuid4(),
                title="Test Task",
                description=None,
                status=TaskStatus.TODO,
                priority=priority,
                assignee=None,
                dependencies=[],
            )
            assert task.priority == priority

    def test_task_with_dependencies(self):
        """Test task with valid dependencies."""
        # Arrange
        dep1 = uuid4()
        dep2 = uuid4()
        task_id = uuid4()

        # Act
        task = Task(
            id=task_id,
            project_id=uuid4(),
            title="Task with dependencies",
            description=None,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee=None,
            dependencies=[dep1, dep2],
        )

        # Assert
        assert len(task.dependencies) == 2
        assert dep1 in task.dependencies
        assert dep2 in task.dependencies

    def test_circular_dependency_self_raises_error(self):
        """Test that task depending on itself raises ValueError."""
        task_id = uuid4()

        with pytest.raises(ValueError, match="Circular dependency detected"):
            Task(
                id=task_id,
                project_id=uuid4(),
                title="Circular task",
                description=None,
                status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                assignee=None,
                dependencies=[task_id],  # Depends on itself
            )

    def test_duplicate_dependencies_raises_error(self):
        """Test that duplicate dependencies raise ValueError."""
        dep = uuid4()

        with pytest.raises(ValueError, match="Duplicate dependencies detected"):
            Task(
                id=uuid4(),
                project_id=uuid4(),
                title="Task",
                description=None,
                status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                assignee=None,
                dependencies=[dep, dep],  # Duplicate
            )

    def test_task_without_assignee(self):
        """Test task creation without assignee."""
        task = Task(
            id=uuid4(),
            project_id=uuid4(),
            title="Unassigned Task",
            description=None,
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee=None,
            dependencies=[],
        )

        assert task.assignee is None

    def test_task_without_description(self):
        """Test task creation without description."""
        task = Task(
            id=uuid4(),
            project_id=uuid4(),
            title="Task",
            description=None,
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee=None,
            dependencies=[],
        )

        assert task.description is None
