"""Pydantic schemas for Task API endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.domain.models.task import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    project_id: UUID = Field(..., description="Project identifier")
    title: str = Field(
        ..., min_length=1, max_length=255, description="Task title"
    )
    description: str | None = Field(None, description="Task description")
    status: TaskStatus = Field(
        default=TaskStatus.TODO, description="Task status"
    )
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM, description="Task priority"
    )
    assignee: str | None = Field(None, description="Assignee identifier")
    dependencies: list[UUID] = Field(
        default_factory=list, description="List of task IDs this task depends on"
    )

    @field_validator("dependencies")
    @classmethod
    def validate_no_duplicates(cls, v: list[UUID]) -> list[UUID]:
        """Validate that dependencies list has no duplicates."""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate dependencies detected")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "project_id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "Implement user authentication",
                    "description": "Add JWT-based authentication to the API",
                    "status": "todo",
                    "priority": "high",
                    "assignee": "dev-001",
                    "dependencies": [],
                }
            ]
        }
    }


class TaskUpdate(BaseModel):
    """Schema for updating task metadata."""

    title: str | None = Field(
        None, min_length=1, max_length=255, description="Task title"
    )
    description: str | None = Field(None, description="Task description")
    status: TaskStatus | None = Field(None, description="Task status")
    priority: TaskPriority | None = Field(None, description="Task priority")
    assignee: str | None = Field(None, description="Assignee identifier")
    dependencies: list[UUID] | None = Field(
        None, description="List of task IDs this task depends on"
    )

    @field_validator("dependencies")
    @classmethod
    def validate_no_duplicates(cls, v: list[UUID] | None) -> list[UUID] | None:
        """Validate that dependencies list has no duplicates."""
        if v is not None and len(v) != len(set(v)):
            raise ValueError("Duplicate dependencies detected")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "in_progress",
                    "assignee": "dev-002",
                }
            ]
        }
    }


class TaskResponse(BaseModel):
    """Response schema for task data."""

    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee: str | None
    dependencies: list[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,  # Pydantic v2 ORM mode
        "json_schema_extra": {
            "examples": [
                {
                    "id": "650e8400-e29b-41d4-a716-446655440000",
                    "project_id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "Implement user authentication",
                    "description": "Add JWT-based authentication to the API",
                    "status": "in_progress",
                    "priority": "high",
                    "assignee": "dev-001",
                    "dependencies": [],
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-02T12:00:00Z",
                }
            ]
        },
    }


class TaskListResponse(BaseModel):
    """Response schema for task list with pagination metadata."""

    tasks: list[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks matching the query")
    skip: int = Field(..., description="Number of tasks skipped")
    limit: int = Field(..., description="Maximum number of tasks returned")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tasks": [],
                    "total": 0,
                    "skip": 0,
                    "limit": 100,
                }
            ]
        }
    }
