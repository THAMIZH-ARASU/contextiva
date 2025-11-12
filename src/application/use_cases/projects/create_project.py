"""Create project use case."""

import logging
from typing import Optional
from uuid import UUID

from src.domain.models.project import IProjectRepository, Project
from src.shared.utils.errors import ProjectAlreadyExistsError

logger = logging.getLogger(__name__)


class CreateProjectUseCase:
    """Use case for creating a new project."""

    def __init__(self, project_repo: IProjectRepository) -> None:
        """Initialize use case with dependencies.
        
        Args:
            project_repo: Repository for project operations.
        """
        self.project_repo = project_repo

    async def execute(
        self,
        name: str,
        owner_id: UUID,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Project:
        """Execute create project use case.
        
        Args:
            name: Project name (required).
            owner_id: UUID of the project owner.
            description: Project description (optional).
            tags: List of project tags (optional).
            
        Returns:
            Created Project entity.
            
        Raises:
            ProjectAlreadyExistsError: If project with same name exists for owner.
            ValueError: If validation fails.
        """
        logger.info(f"Creating project: {name} for owner: {owner_id}")
        
        # Validate inputs
        if not name or not name.strip():
            raise ValueError("Project name cannot be empty")
            
        # Check if project already exists for this owner
        existing = await self.project_repo.get_by_name_and_owner(
            name=name.strip(),
            owner_id=owner_id,
        )
        
        if existing:
            raise ProjectAlreadyExistsError(
                f"Project '{name}' already exists for this owner"
            )
        
        # Create project
        project = Project.create(
            name=name.strip(),
            owner_id=owner_id,
            description=description,
            tags=tags or [],
        )
        
        # Save to repository
        created_project = await self.project_repo.create(project)
        
        logger.info(f"Project created successfully: {created_project.id}")
        
        return created_project
