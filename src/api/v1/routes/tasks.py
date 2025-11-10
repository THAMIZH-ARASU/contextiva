"""Task management API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.api.dependencies import get_current_user, get_task_repository
from src.api.v1.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from src.domain.models.task import ITaskRepository, Task, TaskPriority, TaskStatus
from src.domain.models.user import User
from src.shared.utils.errors import TaskNotFoundError

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    task_repo: ITaskRepository = Depends(get_task_repository),
) -> TaskResponse:
    """
    Create a new task linked to a project.

    Args:
        task_data: The task creation data
        current_user: The authenticated user (from JWT token)
        task_repo: The task repository dependency

    Returns:
        The created task

    Raises:
        HTTPException: 401 if unauthorized, 422 if validation fails
    """
    # Create domain entity from schema
    task = Task(
        id=uuid4(),
        project_id=task_data.project_id,
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        priority=task_data.priority,
        assignee=task_data.assignee,
        dependencies=task_data.dependencies,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Persist to database
    try:
        created_task = await task_repo.create(task)
    except ValueError as e:
        # Catch circular dependency or duplicate dependency errors
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # Return response schema
    return TaskResponse.model_validate(created_task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    project_id: UUID,
    status_filter: TaskStatus | None = None,
    assignee: str | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    task_repo: ITaskRepository = Depends(get_task_repository),
) -> TaskListResponse:
    """
    List all tasks for a project with optional filtering and pagination.

    Args:
        project_id: Project identifier (required query parameter)
        status_filter: Optional status filter (todo, in_progress, done, blocked)
        assignee: Optional assignee filter
        skip: Number of tasks to skip (default: 0)
        limit: Maximum number of tasks to return (default: 100, max: 1000)
        current_user: The authenticated user (from JWT token)
        task_repo: The task repository dependency

    Returns:
        List of tasks with pagination metadata

    Raises:
        HTTPException: 401 if unauthorized
    """
    # Enforce max limit to prevent abuse
    if limit > 1000:
        limit = 1000

    # Fetch tasks based on filters
    if status_filter and assignee:
        # Combined filter: fetch by status first, then filter by assignee in memory
        # (Alternative: add combined repository method for better performance)
        tasks = await task_repo.get_by_status(
            project_id=project_id, status=status_filter, skip=skip, limit=limit
        )
        tasks = [t for t in tasks if t.assignee == assignee]
    elif status_filter:
        tasks = await task_repo.get_by_status(
            project_id=project_id, status=status_filter, skip=skip, limit=limit
        )
    elif assignee:
        # Fetch all tasks by assignee, then filter by project in memory
        # Note: get_by_assignee doesn't accept project_id in the interface
        all_assignee_tasks = await task_repo.get_by_assignee(
            assignee=assignee, skip=0, limit=10000  # Large limit to get all
        )
        tasks = [t for t in all_assignee_tasks if t.project_id == project_id][skip : skip + limit]
    else:
        tasks = await task_repo.get_by_project(
            project_id=project_id, skip=skip, limit=limit
        )

    # Get total count (approximation for now)
    total = len(tasks) + skip

    # Convert to response schemas
    task_responses = [TaskResponse.model_validate(task) for task in tasks]

    return TaskListResponse(tasks=task_responses, total=total, skip=skip, limit=limit)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    task_repo: ITaskRepository = Depends(get_task_repository),
) -> TaskResponse:
    """
    Retrieve a single task by its ID.

    Args:
        task_id: Task identifier
        current_user: The authenticated user (from JWT token)
        task_repo: The task repository dependency

    Returns:
        The requested task

    Raises:
        HTTPException: 401 if unauthorized, 404 if task not found
    """
    # Retrieve task from repository
    task = await task_repo.get_by_id(task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return TaskResponse.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    update_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    task_repo: ITaskRepository = Depends(get_task_repository),
) -> TaskResponse:
    """
    Update a task (status, priority, assignee, dependencies, etc.).

    Args:
        task_id: Task identifier
        update_data: The task update data
        current_user: The authenticated user (from JWT token)
        task_repo: The task repository dependency

    Returns:
        The updated task

    Raises:
        HTTPException: 401 if unauthorized, 404 if task not found, 422 if validation fails
    """
    # Retrieve existing task
    task = await task_repo.get_by_id(task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Apply partial updates (only update fields that are provided)
    if update_data.title is not None:
        task.title = update_data.title
    if update_data.description is not None:
        task.description = update_data.description
    if update_data.status is not None:
        task.status = update_data.status
    if update_data.priority is not None:
        task.priority = update_data.priority
    if update_data.assignee is not None:
        task.assignee = update_data.assignee
    if update_data.dependencies is not None:
        # Validate circular dependency
        if task.id in update_data.dependencies:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Circular dependency detected: task cannot depend on itself",
            )
        task.dependencies = update_data.dependencies

    # Update timestamp
    task.updated_at = datetime.now(timezone.utc)

    # Persist changes
    try:
        updated_task = await task_repo.update(task)
    except ValueError as e:
        # Catch validation errors from domain model
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return TaskResponse.model_validate(updated_task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    task_repo: ITaskRepository = Depends(get_task_repository),
) -> Response:
    """
    Delete a task.

    Args:
        task_id: Task identifier
        current_user: The authenticated user (from JWT token)
        task_repo: The task repository dependency

    Returns:
        Response with 204 No Content

    Raises:
        HTTPException: 401 if unauthorized, 404 if task not found
    """
    # Check if task exists
    task = await task_repo.get_by_id(task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Delete the task
    await task_repo.delete(task_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
