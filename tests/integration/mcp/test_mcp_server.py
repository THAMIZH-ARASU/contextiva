"""Integration tests for MCP server initialization and dependencies."""

import pytest
from unittest.mock import AsyncMock, patch

from src.mcp.context import MCPContext
from src.shared.config.settings import load_settings


@pytest.mark.asyncio
async def test_mcp_context_initialization():
    """Test MCP context initializes successfully.
    
    Arrange: Create MCP context with settings.
    Act: Initialize context.
    Assert: Context is initialized and resources are available.
    """
    # Arrange
    settings = load_settings()
    context = MCPContext(settings=settings)
    
    # Mock database pool initialization
    with patch("src.mcp.context.init_pool") as mock_init_pool:
        mock_pool = AsyncMock()
        mock_init_pool.return_value = mock_pool
        
        # Act
        await context.initialize()
        
        # Assert
        assert context._pool is not None
        mock_init_pool.assert_called_once()
        
        # Cleanup
        await context.cleanup()


@pytest.mark.asyncio
async def test_mcp_context_get_repositories():
    """Test MCP context can create repository instances.
    
    Arrange: Initialize MCP context.
    Act: Get various repositories.
    Assert: Repositories are created successfully.
    """
    # Arrange
    settings = load_settings()
    context = MCPContext(settings=settings)
    
    with patch("src.mcp.context.init_pool") as mock_init_pool:
        mock_pool = AsyncMock()
        mock_init_pool.return_value = mock_pool
        
        await context.initialize()
        
        # Act
        user_repo = await context.get_user_repository()
        project_repo = await context.get_project_repository()
        document_repo = await context.get_document_repository()
        task_repo = await context.get_task_repository()
        knowledge_repo = await context.get_knowledge_repository()
        
        # Assert
        assert user_repo is not None
        assert project_repo is not None
        assert document_repo is not None
        assert task_repo is not None
        assert knowledge_repo is not None
        
        # Cleanup
        await context.cleanup()


@pytest.mark.asyncio
async def test_mcp_context_authenticate_user():
    """Test MCP context can authenticate users via JWT.
    
    Arrange: Create MCP context and mock user repository.
    Act: Authenticate user with valid token.
    Assert: User is authenticated successfully.
    """
    # Arrange
    settings = load_settings()
    context = MCPContext(settings=settings)
    
    # Mock database pool and user repository
    with patch("src.mcp.context.init_pool") as mock_init_pool:
        mock_pool = AsyncMock()
        mock_init_pool.return_value = mock_pool
        
        await context.initialize()
        
        # Mock verify_token
        with patch("src.mcp.context.verify_token") as mock_verify_token:
            mock_verify_token.return_value = {"sub": "testuser"}
            
            # Mock user repository
            with patch.object(
                context, "get_user_repository"
            ) as mock_get_user_repo:
                from uuid import uuid4
                from datetime import datetime, timezone
                from src.domain.models.user import User
                
                mock_user = User(
                    id=uuid4(),
                    username="testuser",
                    email="test@example.com",
                    hashed_password="hashed",
                    is_active=True,
                    roles=["user"],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                
                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_username.return_value = mock_user
                mock_get_user_repo.return_value = mock_user_repo
                
                # Act
                user = await context.authenticate_user("fake_token")
                
                # Assert
                assert user is not None
                assert user.username == "testuser"
                assert user.is_active is True
        
        # Cleanup
        await context.cleanup()


@pytest.mark.asyncio
async def test_mcp_context_authenticate_user_invalid_token():
    """Test MCP context rejects invalid JWT token.
    
    Arrange: Create MCP context with invalid token.
    Act: Attempt to authenticate user.
    Assert: UnauthorizedAccessError is raised.
    """
    # Arrange
    from src.shared.utils.errors import UnauthorizedAccessError
    
    settings = load_settings()
    context = MCPContext(settings=settings)
    
    with patch("src.mcp.context.init_pool") as mock_init_pool:
        mock_pool = AsyncMock()
        mock_init_pool.return_value = mock_pool
        
        await context.initialize()
        
        # Mock verify_token to raise exception
        with patch("src.mcp.context.verify_token") as mock_verify_token:
            mock_verify_token.side_effect = Exception("Invalid token")
            
            # Act & Assert
            with pytest.raises(UnauthorizedAccessError):
                await context.authenticate_user("invalid_token")
        
        # Cleanup
        await context.cleanup()


@pytest.mark.asyncio
async def test_mcp_context_cleanup():
    """Test MCP context cleanup closes resources.
    
    Arrange: Initialize MCP context.
    Act: Call cleanup.
    Assert: Database pool is closed.
    """
    # Arrange
    settings = load_settings()
    context = MCPContext(settings=settings)
    
    with patch("src.mcp.context.init_pool") as mock_init_pool:
        mock_pool = AsyncMock()
        mock_pool.close = AsyncMock()
        mock_init_pool.return_value = mock_pool
        
        await context.initialize()
        
        # Act
        await context.cleanup()
        
        # Assert
        mock_pool.close.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_context_get_repository_before_init():
    """Test get_repository raises error if context not initialized.
    
    Arrange: Create MCP context without initialization.
    Act: Attempt to get repository.
    Assert: RuntimeError is raised.
    """
    # Arrange
    settings = load_settings()
    context = MCPContext(settings=settings)
    
    # Act & Assert
    with pytest.raises(RuntimeError, match="Context not initialized"):
        await context.get_user_repository()
