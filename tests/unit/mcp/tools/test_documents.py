"""Unit tests for MCP document tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.domain.models.user import User
from src.mcp.context import MCPContext
from src.mcp.tools.documents import IngestDocumentTool
from src.shared.utils.errors import ProjectNotFoundError


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
def mock_ingest_result():
    """Create a mock ingestion result."""
    result = MagicMock()
    result.document_id = uuid4()
    result.chunks_created = 5
    return result


class TestIngestDocumentTool:
    """Test suite for IngestDocumentTool."""
    
    @pytest.mark.asyncio
    async def test_execute_with_valid_document(
        self, mock_context, mock_user, mock_ingest_result
    ):
        """Test ingest_document with valid document.
        
        Arrange: Set up mock context, user, and use case.
        Act: Execute ingest_document tool.
        Assert: Document is ingested successfully.
        """
        # Arrange
        tool = IngestDocumentTool(context=mock_context)
        project_id = str(uuid4())
        
        # Mock repositories
        mock_project_repo = AsyncMock()
        mock_document_repo = AsyncMock()
        mock_knowledge_repo = AsyncMock()
        mock_context.get_project_repository.return_value = mock_project_repo
        mock_context.get_document_repository.return_value = mock_document_repo
        mock_context.get_knowledge_repository.return_value = mock_knowledge_repo
        
        # Mock use case execution
        with patch(
            "src.mcp.tools.documents.IngestKnowledgeUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_ingest_result
            mock_use_case_class.return_value = mock_use_case
            
            # Act
            result = await tool.execute(
                project_id=project_id,
                content="This is a test document content.",
                filename="test.txt",
                content_type="text/plain",
                metadata={"source": "test"},
                user=mock_user,
            )
            
            # Assert
            assert result["document_id"] == str(mock_ingest_result.document_id)
            assert result["status"] == "ingested"
            assert result["chunks_created"] == 5
            assert result["filename"] == "test.txt"
            assert result["content_type"] == "text/plain"
            
            # Verify use case was called correctly
            mock_use_case.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_without_optional_params(
        self, mock_context, mock_user, mock_ingest_result
    ):
        """Test ingest_document without optional parameters.
        
        Arrange: Set up mock without filename/metadata.
        Act: Execute ingest_document tool.
        Assert: Document is ingested with defaults.
        """
        # Arrange
        tool = IngestDocumentTool(context=mock_context)
        project_id = str(uuid4())
        
        mock_project_repo = AsyncMock()
        mock_document_repo = AsyncMock()
        mock_knowledge_repo = AsyncMock()
        mock_context.get_project_repository.return_value = mock_project_repo
        mock_context.get_document_repository.return_value = mock_document_repo
        mock_context.get_knowledge_repository.return_value = mock_knowledge_repo
        
        with patch(
            "src.mcp.tools.documents.IngestKnowledgeUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_ingest_result
            mock_use_case_class.return_value = mock_use_case
            
            # Act
            result = await tool.execute(
                project_id=project_id,
                content="Test content",
                user=mock_user,
            )
            
            # Assert
            assert result["filename"] == "untitled.txt"
            assert result["content_type"] == "text/plain"
    
    @pytest.mark.asyncio
    async def test_execute_without_user(self, mock_context):
        """Test ingest_document without authenticated user.
        
        Arrange: Set up tool without user.
        Act: Execute ingest_document tool.
        Assert: ValueError is raised.
        """
        # Arrange
        tool = IngestDocumentTool(context=mock_context)
        
        # Act & Assert
        with pytest.raises(ValueError, match="User authentication required"):
            await tool.execute(
                project_id=str(uuid4()),
                content="Test content",
            )
    
    @pytest.mark.asyncio
    async def test_execute_with_invalid_project_id(self, mock_context, mock_user):
        """Test ingest_document with invalid project_id format.
        
        Arrange: Set up tool with invalid UUID.
        Act: Execute ingest_document tool.
        Assert: ValueError is raised.
        """
        # Arrange
        tool = IngestDocumentTool(context=mock_context)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid project_id format"):
            await tool.execute(
                project_id="not-a-uuid",
                content="Test content",
                user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_execute_with_nonexistent_project(
        self, mock_context, mock_user
    ):
        """Test ingest_document with nonexistent project.
        
        Arrange: Set up mock to raise ProjectNotFoundError.
        Act: Execute ingest_document tool.
        Assert: ProjectNotFoundError is raised.
        """
        # Arrange
        tool = IngestDocumentTool(context=mock_context)
        project_id = str(uuid4())
        
        mock_project_repo = AsyncMock()
        mock_document_repo = AsyncMock()
        mock_knowledge_repo = AsyncMock()
        mock_context.get_project_repository.return_value = mock_project_repo
        mock_context.get_document_repository.return_value = mock_document_repo
        mock_context.get_knowledge_repository.return_value = mock_knowledge_repo
        
        with patch(
            "src.mcp.tools.documents.IngestKnowledgeUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.side_effect = ProjectNotFoundError(
                f"Project {project_id} not found"
            )
            mock_use_case_class.return_value = mock_use_case
            
            # Act & Assert
            with pytest.raises(ProjectNotFoundError):
                await tool.execute(
                    project_id=project_id,
                    content="Test content",
                    user=mock_user,
                )
    
    def test_get_schema(self, mock_context):
        """Test get_schema returns valid MCP tool schema.
        
        Arrange: Create tool instance.
        Act: Get tool schema.
        Assert: Schema contains required fields.
        """
        # Arrange
        tool = IngestDocumentTool(context=mock_context)
        
        # Act
        schema = tool.get_schema()
        
        # Assert
        assert schema["name"] == "ingest_document"
        assert "description" in schema
        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"
        assert "project_id" in schema["parameters"]["properties"]
        assert "content" in schema["parameters"]["properties"]
        assert "filename" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["project_id", "content"]
