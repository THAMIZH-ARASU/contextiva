"""Unit tests for QueryKnowledgeUseCase."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.use_cases.knowledge.query_knowledge import (
    QueryKnowledgeUseCase,
    QueryKnowledgeResult,
)
from src.domain.models.knowledge import KnowledgeItem
from src.domain.models.project import Project
from src.shared.config.settings import Settings, RAGSettings
from src.shared.utils.errors import ProjectNotFoundError, UnauthorizedAccessError


@pytest.fixture
def mock_knowledge_repo():
    """Mock knowledge repository."""
    return AsyncMock()


@pytest.fixture
def mock_project_repo():
    """Mock project repository."""
    return AsyncMock()


@pytest.fixture
def mock_settings():
    """Mock settings with RAG configuration."""
    settings = MagicMock(spec=Settings)
    settings.rag = RAGSettings(default_top_k=5, max_top_k=50)
    return settings


@pytest.fixture
def mock_embedding_provider():
    """Mock embedding provider."""
    provider = AsyncMock()
    provider.embed_text = AsyncMock(return_value=[0.1] * 1536)
    return provider


@pytest.fixture(autouse=True)
def mock_provider_factory(mock_embedding_provider):
    """Mock ProviderFactory for all tests."""
    with patch('src.application.use_cases.knowledge.query_knowledge.ProviderFactory') as mock_factory:
        mock_factory.get_embedding_provider.return_value = mock_embedding_provider
        yield mock_factory


@pytest.fixture
def use_case(mock_knowledge_repo, mock_project_repo, mock_settings):
    """Create use case with mocked dependencies."""
    return QueryKnowledgeUseCase(
        knowledge_repo=mock_knowledge_repo,
        project_repo=mock_project_repo,
        settings=mock_settings,
    )


@pytest.mark.asyncio
async def test_execute_success(use_case, mock_knowledge_repo, mock_project_repo):
    """Test successful query execution with valid inputs."""
    # Arrange
    project_id = uuid4()
    user_id = uuid4()
    
    mock_project = Project(name="Test Project", owner_id=user_id)
    mock_project.id = project_id
    mock_project_repo.get_by_id.return_value = mock_project
    
    mock_items = [
        (
            KnowledgeItem(
                id=uuid4(),
                document_id=uuid4(),
                chunk_text="test chunk",
                chunk_index=0,
                embedding=[0.1] * 1536,
                metadata={},
                created_at=datetime.utcnow(),
            ),
            0.95,
        )
    ]
    mock_knowledge_repo.vector_search.return_value = mock_items
    
    # Act
    result = await use_case.execute(
        project_id=project_id,
        query_text="test query",
        user_id=user_id,
    )
    
    # Assert
    assert isinstance(result, QueryKnowledgeResult)
    assert result.total_results == 1
    assert len(result.results) == 1
    assert result.results[0][1] == 0.95


@pytest.mark.asyncio
async def test_execute_project_not_found(use_case, mock_project_repo):
    """Test ProjectNotFoundError is raised when project doesn't exist."""
    # Arrange
    project_id = uuid4()
    user_id = uuid4()
    mock_project_repo.get_by_id.return_value = None
    
    # Act & Assert
    with pytest.raises(ProjectNotFoundError, match=f"Project {project_id} not found"):
        await use_case.execute(
            project_id=project_id,
            query_text="test",
            user_id=user_id,
        )


@pytest.mark.asyncio
async def test_execute_unauthorized_access(use_case, mock_project_repo):
    """Test UnauthorizedAccessError is raised when user doesn't own project."""
    # Arrange
    project_id = uuid4()
    owner_id = uuid4()
    unauthorized_user_id = uuid4()
    
    mock_project = Project(name="Test Project", owner_id=owner_id)
    mock_project.id = project_id
    mock_project_repo.get_by_id.return_value = mock_project
    
    # Act & Assert
    with pytest.raises(UnauthorizedAccessError):
        await use_case.execute(
            project_id=project_id,
            query_text="test",
            user_id=unauthorized_user_id,
        )


@pytest.mark.asyncio
async def test_execute_uses_default_top_k(use_case, mock_knowledge_repo, mock_project_repo, mock_settings):
    """Test that default top_k from settings is used when not provided."""
    # Arrange
    project_id = uuid4()
    user_id = uuid4()
    
    mock_project = Project(name="Test Project", owner_id=user_id)
    mock_project.id = project_id
    mock_project_repo.get_by_id.return_value = mock_project
    mock_knowledge_repo.vector_search.return_value = []
    
    # Act
    await use_case.execute(
        project_id=project_id,
        query_text="test",
        user_id=user_id,
    )
    
    # Assert
    mock_knowledge_repo.vector_search.assert_called_once()
    call_args = mock_knowledge_repo.vector_search.call_args
    assert call_args.kwargs["top_k"] == mock_settings.rag.default_top_k


@pytest.mark.asyncio
async def test_execute_uses_custom_top_k(use_case, mock_knowledge_repo, mock_project_repo):
    """Test that custom top_k value is used when provided."""
    # Arrange
    project_id = uuid4()
    user_id = uuid4()
    custom_top_k = 10
    
    mock_project = Project(name="Test Project", owner_id=user_id)
    mock_project.id = project_id
    mock_project_repo.get_by_id.return_value = mock_project
    mock_knowledge_repo.vector_search.return_value = []
    
    # Act
    await use_case.execute(
        project_id=project_id,
        query_text="test",
        user_id=user_id,
        top_k=custom_top_k,
    )
    
    # Assert
    mock_knowledge_repo.vector_search.assert_called_once()
    call_args = mock_knowledge_repo.vector_search.call_args
    assert call_args.kwargs["top_k"] == custom_top_k


@pytest.mark.asyncio
async def test_execute_enforces_max_top_k(use_case, mock_knowledge_repo, mock_project_repo, mock_settings):
    """Test that max top_k is enforced."""
    # Arrange
    project_id = uuid4()
    user_id = uuid4()
    excessive_top_k = 100  # Greater than max_top_k (50)
    
    mock_project = Project(name="Test Project", owner_id=user_id)
    mock_project.id = project_id
    mock_project_repo.get_by_id.return_value = mock_project
    mock_knowledge_repo.vector_search.return_value = []
    
    # Act
    await use_case.execute(
        project_id=project_id,
        query_text="test",
        user_id=user_id,
        top_k=excessive_top_k,
    )
    
    # Assert
    mock_knowledge_repo.vector_search.assert_called_once()
    call_args = mock_knowledge_repo.vector_search.call_args
    assert call_args.kwargs["top_k"] == mock_settings.rag.max_top_k


@pytest.mark.asyncio
async def test_execute_empty_results(use_case, mock_knowledge_repo, mock_project_repo):
    """Test empty results scenario (no documents in project)."""
    # Arrange
    project_id = uuid4()
    user_id = uuid4()
    
    mock_project = Project(name="Test Project", owner_id=user_id)
    mock_project.id = project_id
    mock_project_repo.get_by_id.return_value = mock_project
    mock_knowledge_repo.vector_search.return_value = []
    
    # Act
    result = await use_case.execute(
        project_id=project_id,
        query_text="test",
        user_id=user_id,
    )
    
    # Assert
    assert result.total_results == 0
    assert len(result.results) == 0
