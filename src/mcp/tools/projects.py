"""MCP tools for project management operations."""

import logging
from typing import Any, Optional
from uuid import UUID

from src.application.use_cases.projects.create_project import CreateProjectUseCase
from src.domain.models.user import User
from src.mcp.context import MCPContext
from src.shared.utils.errors import ProjectAlreadyExistsError

logger = logging.getLogger(__name__)


class CreateProjectTool:
    """MCP tool for creating a new project.
    
    Provides create_project functionality to MCP clients, mapping tool
    parameters to Application layer use case.
    """

    def __init__(self, context: MCPContext) -> None:
        """Initialize tool with MCP context.
        
        Args:
            context: MCP context for dependency injection.
        """
        self.context = context
        
    async def execute(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        user: Optional[User] = None,
    ) -> dict[str, Any]:
        """Execute create_project tool.
        
        Args:
            name: Project name (required).
            description: Project description (optional).
            tags: List of project tags (optional).
            user: Authenticated user (required).
            
        Returns:
            Dictionary containing project_id and metadata in MCP-compliant format.
            
        Raises:
            ProjectAlreadyExistsError: If project with same name exists for user.
            ValueError: If validation fails.
        """
        if not user:
            raise ValueError("User authentication required for create_project")
            
        logger.info(f"Creating project: {name} for user: {user.username}")
        
        # Get project repository
        project_repo = await self.context.get_project_repository()
        
        # Create and execute use case
        use_case = CreateProjectUseCase(project_repo=project_repo)
        
        project = await use_case.execute(
            name=name,
            description=description,
            owner_id=user.id,
            tags=tags or [],
        )
        
        logger.info(f"Project created successfully: {project.id}")
        
        # Return MCP-compliant response
        return {
            "project_id": str(project.id),
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "tags": project.tags,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }
        
    def get_schema(self) -> dict[str, Any]:
        """Get MCP tool schema definition.
        
        Returns:
            MCP tool schema for create_project.
        """
        return {
            "name": "create_project",
            "description": "Create a new project in Contextiva knowledge engine",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Project name (1-200 characters)",
                        "minLength": 1,
                        "maxLength": 200,
                    },
                    "description": {
                        "type": "string",
                        "description": "Project description (optional, max 2000 characters)",
                        "maxLength": 2000,
                    },
                    "tags": {
                        "type": "array",
                        "description": "List of project tags (optional)",
                        "items": {"type": "string"},
                    },
                },
                "required": ["name"],
            },
        }
