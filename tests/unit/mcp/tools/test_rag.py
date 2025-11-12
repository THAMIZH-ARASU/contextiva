"""Unit tests for MCP RAG tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.domain.models.knowledge import KnowledgeItem
from src.domain.models.user import User
from src.mcp.context import MCPContext
from src.mcp.tools.rag import QueryKnowledgeTool
from src.shared.utils.errors import ProjectNotFoundError


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=MCPContext)
    context.settings = MagicMock()
    context.get_cache_service.return_value = None
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
def mock_knowledge_items():
    """Create mock knowledge items."""
    items = []
    for i in range(3):
        item = KnowledgeItem(
            id=uuid4(),
            document_id=uuid4(),
            chunk_text=f"Test chunk {i}",
            chunk_index=i,
            embedding=[0.1] * 1536,
            metadata={"page": i},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        items.append(item)
    return items


@pytest.fixture
def mock_query_result(mock_knowledge_items):
    """Create a mock query result."""
    result = MagicMock()
    result.query_id = uuid4()
    result.results = [
        (mock_knowledge_items[0], 0.95, None, None),
        (mock_knowledge_items[1], 0.85, None, None),
        (mock_knowledge_items[2], 0.75, None, None),
    ]
    result.total_results = 3
    result.synthesized_answer = None
    return result


class TestQueryKnowledgeTool:
    """Test suite for QueryKnowledgeTool."""
    
    @pytest.mark.asyncio
    async def test_execute_with_basic_search(
        self, mock_context, mock_user, mock_query_result
    ):
        """Test query_knowledge with basic vector search.
        
        Arrange: Set up mock context and use case.
        Act: Execute query_knowledge tool.
        Assert: Results are returned successfully.
        """
        # Arrange
        tool = QueryKnowledgeTool(context=mock_context)
        project_id = str(uuid4())
        
        # Mock repositories
        mock_project_repo = AsyncMock()
        mock_knowledge_repo = AsyncMock()
        mock_context.get_project_repository.return_value = mock_project_repo
        mock_context.get_knowledge_repository.return_value = mock_knowledge_repo
        
        # Mock use case execution
        with patch(
            "src.mcp.tools.rag.QueryKnowledgeUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_query_result
            mock_use_case_class.return_value = mock_use_case
            
            # Act
            result = await tool.execute(
                project_id=project_id,
                query_text="What is machine learning?",
                user=mock_user,
            )
            
            # Assert
            assert result["query_id"] == str(mock_query_result.query_id)
            assert result["total_results"] == 3
            assert len(result["results"]) == 3
            assert result["synthesized_answer"] is None
            
            # Check first result structure
            first_result = result["results"][0]
            assert "id" in first_result
            assert "chunk_text" in first_result
            assert first_result["similarity_score"] == 0.95
            assert first_result["bm25_score"] is None
            assert first_result["rerank_score"] is None
            
            # Verify use case was called correctly
            mock_use_case.execute.assert_called_once()
            call_args = mock_use_case.execute.call_args[1]
            assert call_args["use_hybrid_search"] is False
            assert call_args["use_re_ranking"] is False
            assert call_args["use_agentic_rag"] is False
    
    @pytest.mark.asyncio
    async def test_execute_with_hybrid_search(
        self, mock_context, mock_user, mock_knowledge_items
    ):
        """Test query_knowledge with hybrid search enabled.
        
        Arrange: Set up mock with hybrid search results.
        Act: Execute query_knowledge with use_hybrid_search=True.
        Assert: Results include BM25 scores.
        """
        # Arrange
        tool = QueryKnowledgeTool(context=mock_context)
        project_id = str(uuid4())
        
        # Mock result with BM25 scores
        hybrid_result = MagicMock()
        hybrid_result.query_id = uuid4()
        hybrid_result.results = [
            (mock_knowledge_items[0], 0.95, 2.5, None),
            (mock_knowledge_items[1], 0.85, 2.0, None),
        ]
        hybrid_result.total_results = 2
        hybrid_result.synthesized_answer = None
        
        mock_project_repo = AsyncMock()
        mock_knowledge_repo = AsyncMock()
        mock_context.get_project_repository.return_value = mock_project_repo
        mock_context.get_knowledge_repository.return_value = mock_knowledge_repo
        
        with patch(
            "src.mcp.tools.rag.QueryKnowledgeUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = hybrid_result
            mock_use_case_class.return_value = mock_use_case
            
            # Act
            result = await tool.execute(
                project_id=project_id,
                query_text="What is machine learning?",
                use_hybrid_search=True,
                user=mock_user,
            )
            
            # Assert
            assert result["results"][0]["bm25_score"] == 2.5
            assert result["results"][1]["bm25_score"] == 2.0
            
            # Verify use case was called with hybrid flag
            call_args = mock_use_case.execute.call_args[1]
            assert call_args["use_hybrid_search"] is True
    
    @pytest.mark.asyncio
    async def test_execute_with_re_ranking(
        self, mock_context, mock_user, mock_knowledge_items
    ):
        """Test query_knowledge with re-ranking enabled.
        
        Arrange: Set up mock with re-ranking results.
        Act: Execute query_knowledge with use_re_ranking=True.
        Assert: Results include rerank scores.
        """
        # Arrange
        tool = QueryKnowledgeTool(context=mock_context)
        project_id = str(uuid4())
        
        # Mock result with rerank scores
        rerank_result = MagicMock()
        rerank_result.query_id = uuid4()
        rerank_result.results = [
            (mock_knowledge_items[0], 0.95, None, 0.98),
            (mock_knowledge_items[1], 0.85, None, 0.88),
        ]
        rerank_result.total_results = 2
        rerank_result.synthesized_answer = None
        
        mock_project_repo = AsyncMock()
        mock_knowledge_repo = AsyncMock()
        mock_context.get_project_repository.return_value = mock_project_repo
        mock_context.get_knowledge_repository.return_value = mock_knowledge_repo
        
        with patch(
            "src.mcp.tools.rag.QueryKnowledgeUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = rerank_result
            mock_use_case_class.return_value = mock_use_case
            
            # Act
            result = await tool.execute(
                project_id=project_id,
                query_text="What is machine learning?",
                use_re_ranking=True,
                user=mock_user,
            )
            
            # Assert
            assert result["results"][0]["rerank_score"] == 0.98
            assert result["results"][1]["rerank_score"] == 0.88
            
            # Verify use case was called with rerank flag
            call_args = mock_use_case.execute.call_args[1]
            assert call_args["use_re_ranking"] is True
    
    @pytest.mark.asyncio
    async def test_execute_with_agentic_rag(
        self, mock_context, mock_user, mock_query_result
    ):
        """Test query_knowledge with agentic RAG (synthesis) enabled.
        
        Arrange: Set up mock with synthesized answer.
        Act: Execute query_knowledge with use_agentic_rag=True.
        Assert: Results include synthesized answer.
        """
        # Arrange
        tool = QueryKnowledgeTool(context=mock_context)
        project_id = str(uuid4())
        
        # Mock result with synthesized answer
        mock_query_result.synthesized_answer = "Machine learning is a subset of AI..."
        
        mock_project_repo = AsyncMock()
        mock_knowledge_repo = AsyncMock()
        mock_context.get_project_repository.return_value = mock_project_repo
        mock_context.get_knowledge_repository.return_value = mock_knowledge_repo
        
        with patch(
            "src.mcp.tools.rag.QueryKnowledgeUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_query_result
            mock_use_case_class.return_value = mock_use_case
            
            # Act
            result = await tool.execute(
                project_id=project_id,
                query_text="What is machine learning?",
                use_agentic_rag=True,
                user=mock_user,
            )
            
            # Assert
            assert result["synthesized_answer"] == "Machine learning is a subset of AI..."
            
            # Verify use case was called with agentic flag
            call_args = mock_use_case.execute.call_args[1]
            assert call_args["use_agentic_rag"] is True
    
    @pytest.mark.asyncio
    async def test_execute_with_all_flags(
        self, mock_context, mock_user, mock_knowledge_items
    ):
        """Test query_knowledge with all RAG features enabled.
        
        Arrange: Set up mock with all features.
        Act: Execute query_knowledge with all flags True.
        Assert: All features are enabled in use case call.
        """
        # Arrange
        tool = QueryKnowledgeTool(context=mock_context)
        project_id = str(uuid4())
        
        # Mock result with all features
        full_result = MagicMock()
        full_result.query_id = uuid4()
        full_result.results = [
            (mock_knowledge_items[0], 0.95, 2.5, 0.98),
        ]
        full_result.total_results = 1
        full_result.synthesized_answer = "Comprehensive answer..."
        
        mock_project_repo = AsyncMock()
        mock_knowledge_repo = AsyncMock()
        mock_context.get_project_repository.return_value = mock_project_repo
        mock_context.get_knowledge_repository.return_value = mock_knowledge_repo
        
        with patch(
            "src.mcp.tools.rag.QueryKnowledgeUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = full_result
            mock_use_case_class.return_value = mock_use_case
            
            # Act
            result = await tool.execute(
                project_id=project_id,
                query_text="What is machine learning?",
                top_k=5,
                use_hybrid_search=True,
                use_re_ranking=True,
                use_agentic_rag=True,
                user=mock_user,
            )
            
            # Assert
            assert result["results"][0]["similarity_score"] == 0.95
            assert result["results"][0]["bm25_score"] == 2.5
            assert result["results"][0]["rerank_score"] == 0.98
            assert result["synthesized_answer"] == "Comprehensive answer..."
            
            # Verify all flags were passed
            call_args = mock_use_case.execute.call_args[1]
            assert call_args["use_hybrid_search"] is True
            assert call_args["use_re_ranking"] is True
            assert call_args["use_agentic_rag"] is True
            assert call_args["top_k"] == 5
    
    @pytest.mark.asyncio
    async def test_execute_without_user(self, mock_context):
        """Test query_knowledge without authenticated user.
        
        Arrange: Set up tool without user.
        Act: Execute query_knowledge tool.
        Assert: ValueError is raised.
        """
        # Arrange
        tool = QueryKnowledgeTool(context=mock_context)
        
        # Act & Assert
        with pytest.raises(ValueError, match="User authentication required"):
            await tool.execute(
                project_id=str(uuid4()),
                query_text="What is machine learning?",
            )
    
    @pytest.mark.asyncio
    async def test_execute_with_invalid_project_id(self, mock_context, mock_user):
        """Test query_knowledge with invalid project_id format.
        
        Arrange: Set up tool with invalid UUID.
        Act: Execute query_knowledge tool.
        Assert: ValueError is raised.
        """
        # Arrange
        tool = QueryKnowledgeTool(context=mock_context)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid project_id format"):
            await tool.execute(
                project_id="not-a-uuid",
                query_text="What is machine learning?",
                user=mock_user,
            )
    
    def test_get_schema(self, mock_context):
        """Test get_schema returns valid MCP tool schema.
        
        Arrange: Create tool instance.
        Act: Get tool schema.
        Assert: Schema contains required fields.
        """
        # Arrange
        tool = QueryKnowledgeTool(context=mock_context)
        
        # Act
        schema = tool.get_schema()
        
        # Assert
        assert schema["name"] == "query_knowledge"
        assert "description" in schema
        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"
        assert "project_id" in schema["parameters"]["properties"]
        assert "query_text" in schema["parameters"]["properties"]
        assert "use_hybrid_search" in schema["parameters"]["properties"]
        assert "use_re_ranking" in schema["parameters"]["properties"]
        assert "use_agentic_rag" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["project_id", "query_text"]
