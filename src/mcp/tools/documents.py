"""MCP tools for document ingestion operations."""

import logging
from typing import Any, Optional
from uuid import UUID

from src.application.use_cases.ingest_knowledge import IngestKnowledgeUseCase
from src.domain.models.user import User
from src.mcp.context import MCPContext
from src.shared.utils.errors import ProjectNotFoundError

logger = logging.getLogger(__name__)


class IngestDocumentTool:
    """MCP tool for ingesting a document into a project.
    
    Provides ingest_document functionality to MCP clients, mapping tool
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
        project_id: str,
        content: str,
        filename: Optional[str] = None,
        content_type: str = "text/plain",
        metadata: Optional[dict[str, Any]] = None,
        user: Optional[User] = None,
    ) -> dict[str, Any]:
        """Execute ingest_document tool.
        
        Args:
            project_id: UUID of the project (required).
            content: Document content/text (required).
            filename: Document filename (optional).
            content_type: MIME type of content (default: text/plain).
            metadata: Additional metadata (optional).
            user: Authenticated user (required).
            
        Returns:
            Dictionary containing document_id and ingestion status in MCP-compliant format.
            
        Raises:
            ProjectNotFoundError: If project does not exist.
            ValueError: If validation fails.
        """
        if not user:
            raise ValueError("User authentication required for ingest_document")
            
        # Parse project_id
        try:
            project_uuid = UUID(project_id)
        except ValueError as e:
            raise ValueError(f"Invalid project_id format: {e}")
            
        logger.info(f"Ingesting document into project: {project_id} for user: {user.username}")
        
        # Get repositories
        project_repo = await self.context.get_project_repository()
        document_repo = await self.context.get_document_repository()
        knowledge_repo = await self.context.get_knowledge_repository()
        
        # Create and execute use case
        use_case = IngestKnowledgeUseCase(
            project_repo=project_repo,
            document_repo=document_repo,
            knowledge_repo=knowledge_repo,
            settings=self.context.settings,
        )
        
        result = await use_case.execute(
            project_id=project_uuid,
            user_id=user.id,
            content=content,
            filename=filename or "untitled.txt",
            content_type=content_type,
            metadata=metadata,
        )
        
        logger.info(f"Document ingested successfully: {result.document_id}")
        
        # Return MCP-compliant response
        return {
            "document_id": str(result.document_id),
            "status": "ingested",
            "chunks_created": result.chunks_created,
            "filename": filename or "untitled.txt",
            "content_type": content_type,
        }
        
    def get_schema(self) -> dict[str, Any]:
        """Get MCP tool schema definition.
        
        Returns:
            MCP tool schema for ingest_document.
        """
        return {
            "name": "ingest_document",
            "description": "Ingest a document into a Contextiva project for knowledge retrieval",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "UUID of the project to ingest document into",
                        "format": "uuid",
                    },
                    "content": {
                        "type": "string",
                        "description": "Document content/text to ingest",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Document filename (optional)",
                    },
                    "content_type": {
                        "type": "string",
                        "description": "MIME type of content (default: text/plain)",
                        "default": "text/plain",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata (optional)",
                    },
                },
                "required": ["project_id", "content"],
            },
        }
