"""MCP server context and dependency management.

This module provides context management for the MCP server, including
dependency injection for repositories, services, and authentication.
"""

import logging
from typing import Optional

from src.domain.models.document import IDocumentRepository
from src.domain.models.knowledge import IKnowledgeRepository
from src.domain.models.project import IProjectRepository
from src.domain.models.task import ITaskRepository
from src.domain.models.user import IUserRepository, User
from src.infrastructure.cache.redis_cache import RedisCacheService
from src.infrastructure.database.repositories.document_repository import DocumentRepository
from src.infrastructure.database.repositories.knowledge_repository import KnowledgeRepository
from src.infrastructure.database.repositories.project_repository import ProjectRepository
from src.infrastructure.database.repositories.task_repository import TaskRepository
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.shared.config.settings import Settings, load_settings
from src.shared.infrastructure.database.connection import init_pool
from src.shared.utils.errors import UnauthorizedAccessError
from src.shared.utils.security import verify_token

logger = logging.getLogger(__name__)


class MCPContext:
    """Context manager for MCP server dependencies.
    
    Manages shared dependencies including database connections, repositories,
    services, and authentication state.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Initialize MCP context.
        
        Args:
            settings: Optional application settings (loads from env if not provided).
        """
        self.settings = settings or load_settings()
        self._pool = None
        self._cache_service: Optional[RedisCacheService] = None
        
    async def initialize(self) -> None:
        """Initialize database pool and cache connections."""
        logger.info("Initializing MCP server context...")
        self._pool = await init_pool()
        # TODO: Initialize Redis cache service when implemented
        logger.info("MCP server context initialized successfully")
        
    async def cleanup(self) -> None:
        """Clean up resources (close database pool, cache connections)."""
        logger.info("Cleaning up MCP server context...")
        if self._pool:
            await self._pool.close()
        # TODO: Close Redis cache connection when implemented
        logger.info("MCP server context cleaned up successfully")
        
    async def get_user_repository(self) -> IUserRepository:
        """Get user repository instance.
        
        Returns:
            User repository instance.
        """
        if not self._pool:
            raise RuntimeError("Context not initialized. Call initialize() first.")
        return UserRepository(self._pool)
        
    async def get_project_repository(self) -> IProjectRepository:
        """Get project repository instance.
        
        Returns:
            Project repository instance.
        """
        if not self._pool:
            raise RuntimeError("Context not initialized. Call initialize() first.")
        return ProjectRepository()
        
    async def get_document_repository(self) -> IDocumentRepository:
        """Get document repository instance.
        
        Returns:
            Document repository instance.
        """
        if not self._pool:
            raise RuntimeError("Context not initialized. Call initialize() first.")
        return DocumentRepository(self._pool)
        
    async def get_task_repository(self) -> ITaskRepository:
        """Get task repository instance.
        
        Returns:
            Task repository instance.
        """
        if not self._pool:
            raise RuntimeError("Context not initialized. Call initialize() first.")
        return TaskRepository(self._pool)
        
    async def get_knowledge_repository(self) -> IKnowledgeRepository:
        """Get knowledge repository instance.
        
        Returns:
            Knowledge repository instance.
        """
        if not self._pool:
            raise RuntimeError("Context not initialized. Call initialize() first.")
        return KnowledgeRepository(self._pool)
        
    def get_cache_service(self) -> Optional[RedisCacheService]:
        """Get Redis cache service instance.
        
        Returns:
            Optional Redis cache service instance.
        """
        return self._cache_service
        
    async def authenticate_user(self, token: str) -> User:
        """Authenticate user from JWT token.
        
        Args:
            token: JWT authentication token.
            
        Returns:
            Authenticated User entity.
            
        Raises:
            UnauthorizedAccessError: If token is invalid or user not found/inactive.
        """
        try:
            # Verify and decode token
            payload = verify_token(token)
            username: Optional[str] = payload.get("sub")
            
            if username is None:
                raise UnauthorizedAccessError("Invalid token payload: missing subject")
                
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            raise UnauthorizedAccessError("Could not validate credentials")
            
        # Get user from repository
        user_repo = await self.get_user_repository()
        user = await user_repo.get_by_username(username)
        
        if user is None:
            raise UnauthorizedAccessError(f"User not found: {username}")
            
        if not user.is_active:
            raise UnauthorizedAccessError("User account is inactive")
            
        return user
