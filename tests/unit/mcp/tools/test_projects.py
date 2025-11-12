"""Unit tests for MCP project tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.domain.models.project import Project
from src.domain.models.user import User
from src.mcp.context import MCPContext
from src.mcp.tools.projects import CreateProjectTool
from src.shared.utils.errors import ProjectAlreadyExistsError


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=MCPContext)
    context.settings = MagicMock()
    return context


@pytest.fixture
def mock_user():
    """Create a mock user."""
    return User(
        id=uuid4(),
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        roles=["user"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_project():
    """Create a mock project."""
    return Project(
        id=uuid4(),
        name="Test Project",
        description="Test project description",
        owner_id=uuid4(),
        status="Active",
        tags=["test", "unit"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestCreateProjectTool:
    """Test suite for CreateProjectTool."""
    
    @pytest.mark.asyncio
    async def test_execute_with_valid_inputs(
        self, mock_context, mock_user, mock_project
    ):
        """Test create_project with valid inputs.
        
        Arrange: Set up mock context, user, and use case.
        Act: Execute create_project tool.
        Assert: Project is created successfully.
        """
        # Arrange
        tool = CreateProjectTool(context=mock_context)
        
        # Mock project repository
        mock_project_repo = AsyncMock()
        mock_context.get_project_repository.return_value = mock_project_repo
        
        # Mock use case execution
        with patch(
            "src.mcp.tools.projects.CreateProjectUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_project
            mock_use_case_class.return_value = mock_use_case
            
            # Act
            result = await tool.execute(
                name="Test Project",
                description="Test project description",
                tags=["test", "unit"],
                user=mock_user,
            )
            
            # Assert
            assert result["project_id"] == str(mock_project.id)
            assert result["name"] == mock_project.name
            assert result["description"] == mock_project.description
            assert result["status"] == mock_project.status
            assert result["tags"] == mock_project.tags
            assert "created_at" in result
            assert "updated_at" in result
            
            # Verify use case was called correctly
            mock_use_case.execute.assert_called_once_with(
                name="Test Project",
                description="Test project description",
                owner_id=mock_user.id,
                tags=["test", "unit"],
            )
    
    @pytest.mark.asyncio
    async def test_execute_without_optional_params(
        self, mock_context, mock_user, mock_project
    ):
        """Test create_project without optional parameters.
        
        Arrange: Set up mock context and user without description/tags.
        Act: Execute create_project tool.
        Assert: Project is created with defaults.
        """
        # Arrange
        tool = CreateProjectTool(context=mock_context)
        mock_project_repo = AsyncMock()
        mock_context.get_project_repository.return_value = mock_project_repo
        
        with patch(
            "src.mcp.tools.projects.CreateProjectUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_project
            mock_use_case_class.return_value = mock_use_case
            
            # Act
            result = await tool.execute(
                name="Test Project",
                user=mock_user,
            )
            
            # Assert
            assert result["project_id"] == str(mock_project.id)
            
            # Verify use case was called with empty tags
            mock_use_case.execute.assert_called_once_with(
                name="Test Project",
                description=None,
                owner_id=mock_user.id,
                tags=[],
            )
    
    @pytest.mark.asyncio
    async def test_execute_without_user(self, mock_context):
        """Test create_project without authenticated user.
        
        Arrange: Set up tool without user.
        Act: Execute create_project tool.
        Assert: ValueError is raised.
        """
        # Arrange
        tool = CreateProjectTool(context=mock_context)
        
        # Act & Assert
        with pytest.raises(ValueError, match="User authentication required"):
            await tool.execute(name="Test Project")
    
    @pytest.mark.asyncio
    async def test_execute_with_duplicate_project_name(
        self, mock_context, mock_user
    ):
        """Test create_project with duplicate project name.
        
        Arrange: Set up mock to raise ProjectAlreadyExistsError.
        Act: Execute create_project tool.
        Assert: ProjectAlreadyExistsError is raised.
        """
        # Arrange
        tool = CreateProjectTool(context=mock_context)
        mock_project_repo = AsyncMock()
        mock_context.get_project_repository.return_value = mock_project_repo
        
        with patch(
            "src.mcp.tools.projects.CreateProjectUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.side_effect = ProjectAlreadyExistsError(
                "Project 'Test Project' already exists"
            )
            mock_use_case_class.return_value = mock_use_case
            
            # Act & Assert
            with pytest.raises(ProjectAlreadyExistsError):
                await tool.execute(
                    name="Test Project",
                    user=mock_user,
                )
    
    def test_get_schema(self, mock_context):
        """Test get_schema returns valid MCP tool schema.
        
        Arrange: Create tool instance.
        Act: Get tool schema.
        Assert: Schema contains required fields.
        """
        # Arrange
        tool = CreateProjectTool(context=mock_context)
        
        # Act
        schema = tool.get_schema()
        
        # Assert
        assert schema["name"] == "create_project"
        assert "description" in schema
        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"
        assert "name" in schema["parameters"]["properties"]
        assert "description" in schema["parameters"]["properties"]
        assert "tags" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["name"]
