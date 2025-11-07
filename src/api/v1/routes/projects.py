"""Project management API routes."""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.api.dependencies import get_current_user, get_project_repository
from src.api.v1.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from src.domain.models.project import IProjectRepository, Project
from src.domain.models.user import User
from src.shared.utils.errors import ProjectNotFoundError


router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    project_repo: IProjectRepository = Depends(get_project_repository),
) -> ProjectResponse:
    """
    Create a new project.
    
    Args:
        project_data: The project creation data
        current_user: The authenticated user (from JWT token)
        project_repo: The project repository dependency
        
    Returns:
        The created project with ID
        
    Raises:
        HTTPException: 422 if validation fails
    """
    # Create domain entity from schema
    project = Project(
        name=project_data.name,
        description=project_data.description,
        tags=project_data.tags,
    )
    
    # Persist to database
    created_project = await project_repo.create(project)
    
    # Return response schema
    return ProjectResponse.model_validate(created_project)


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    project_repo: IProjectRepository = Depends(get_project_repository),
) -> List[ProjectResponse]:
    """
    List all projects with pagination.
    
    Args:
        skip: Number of projects to skip (default: 0)
        limit: Maximum number of projects to return (default: 100, max: 1000)
        current_user: The authenticated user (from JWT token)
        project_repo: The project repository dependency
        
    Returns:
        List of projects
    """
    # Enforce max limit to prevent abuse
    if limit > 1000:
        limit = 1000
    
    # Fetch projects from repository
    projects = await project_repo.get_all(limit=limit, offset=skip)
    
    # Convert to response schemas
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    project_repo: IProjectRepository = Depends(get_project_repository),
) -> ProjectResponse:
    """
    Get a single project by ID.
    
    Args:
        project_id: The project UUID
        current_user: The authenticated user (from JWT token)
        project_repo: The project repository dependency
        
    Returns:
        The requested project
        
    Raises:
        HTTPException: 404 if project not found
    """
    project = await project_repo.get_by_id(project_id)
    
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
    
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    project_repo: IProjectRepository = Depends(get_project_repository),
) -> ProjectResponse:
    """
    Update an existing project.
    
    Args:
        project_id: The project UUID
        project_data: The project update data (only provided fields are updated)
        current_user: The authenticated user (from JWT token)
        project_repo: The project repository dependency
        
    Returns:
        The updated project
        
    Raises:
        HTTPException: 404 if project not found
    """
    # Fetch existing project
    existing_project = await project_repo.get_by_id(project_id)
    
    if existing_project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
    
    # Update only provided fields
    update_data = project_data.model_dump(exclude_unset=True)
    
    if "name" in update_data:
        existing_project.name = update_data["name"]
    if "description" in update_data:
        existing_project.description = update_data["description"]
    if "status" in update_data:
        existing_project.status = update_data["status"]
    if "tags" in update_data:
        existing_project.tags = update_data["tags"]
    
    # Validate updated entity (triggers __post_init__)
    try:
        updated_project = Project(
            id=existing_project.id,
            name=existing_project.name,
            description=existing_project.description,
            status=existing_project.status,
            tags=existing_project.tags,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    
    # Persist changes
    try:
        await project_repo.update(updated_project)
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
    
    return ProjectResponse.model_validate(updated_project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    project_repo: IProjectRepository = Depends(get_project_repository),
) -> Response:
    """
    Delete a project.
    
    Args:
        project_id: The project UUID
        current_user: The authenticated user (from JWT token)
        project_repo: The project repository dependency
        
    Returns:
        204 No Content on success
        
    Raises:
        HTTPException: 404 if project not found
    """
    try:
        await project_repo.delete(project_id)
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
