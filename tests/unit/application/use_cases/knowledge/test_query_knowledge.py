"""Unit tests for QueryKnowledgeUseCase."""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch

from src.application.use_cases.knowledge.query_knowledge import (
    QueryKnowledgeUseCase,
    QueryKnowledgeResult,
)
from src.domain.models.knowledge import KnowledgeItem
from src.domain.models.project import Project
from src.shared.utils.errors import ProjectNotFoundError, UnauthorizedAccessError


@pytest.fixture
def mock_knowledge_repo():
    """Mock knowledge repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_project_repo():
    """Mock project repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_settings():
    """Mock settings."""
    settings = MagicMock()
    settings.rag.default_top_k = 5
    settings.rag.max_top_k = 50
    settings.rag.use_hybrid_search = False
    settings.rag.use_reranking = False
    settings.rag.hybrid_search_weight_vector = 0.7
    settings.rag.hybrid_search_weight_bm25 = 0.3
    settings.rag.reranking_model = "gpt-4o-mini"
    settings.rag.reranking_top_k = 10
    settings.rag.cache_enabled = True
    settings.rag.cache_ttl = 3600
    settings.rag.cache_key_prefix = "rag:query:"
    return settings


@pytest.fixture
def mock_cache_service():
    """Mock Redis cache service."""
    cache = AsyncMock()
    cache.generate_cache_key = MagicMock(return_value="test_cache_key")
    return cache


@pytest.fixture
def sample_project():
    """Sample project for testing."""
    return Project(
        id=uuid4(),
        name="Test Project",
        owner_id=uuid4(),
        description="Test project description",
    )


@pytest.fixture
def sample_knowledge_items():
    """Sample knowledge items for testing."""
    return [
        KnowledgeItem(
            id=uuid4(),
            document_id=uuid4(),
            chunk_text="Machine learning is awesome",
            chunk_index=0,
            embedding=[0.1] * 1536,
            metadata={"source": "test1"},
            created_at=datetime.utcnow(),
        ),
        KnowledgeItem(
            id=uuid4(),
            document_id=uuid4(),
            chunk_text="Deep learning uses neural networks",
            chunk_index=1,
            embedding=[0.2] * 1536,
            metadata={"source": "test2"},
            created_at=datetime.utcnow(),
        ),
        KnowledgeItem(
            id=uuid4(),
            document_id=uuid4(),
            chunk_text="Natural language processing is important",
            chunk_index=2,
            embedding=[0.3] * 1536,
            metadata={"source": "test3"},
            created_at=datetime.utcnow(),
        ),
    ]


@pytest.mark.asyncio
class TestQueryKnowledgeUseCase:
    """Test cases for QueryKnowledgeUseCase."""

    async def test_execute_vector_search_only(
        self,
        mock_knowledge_repo,
        mock_project_repo,
        mock_settings,
        mock_cache_service,
        sample_project,
        sample_knowledge_items,
    ):
        """Test basic vector search without hybrid or re-ranking."""
        # Arrange
        mock_project_repo.get_by_id = AsyncMock(return_value=sample_project)
        mock_cache_service.get = AsyncMock(return_value=None)  # Cache miss
        
        # Mock vector search results
        vector_results = [
            (sample_knowledge_items[0], 0.95),
            (sample_knowledge_items[1], 0.85),
            (sample_knowledge_items[2], 0.75),
        ]
        mock_knowledge_repo.vector_search = AsyncMock(return_value=vector_results)
        
        # Mock embedding provider
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_text = AsyncMock(return_value=[0.1] * 1536)
        
        use_case = QueryKnowledgeUseCase(
            knowledge_repo=mock_knowledge_repo,
            project_repo=mock_project_repo,
            settings=mock_settings,
            cache_service=mock_cache_service,
        )
        
        # Act
        with patch(
            "src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider",
            return_value=mock_embedding_provider,
        ):
            result = await use_case.execute(
                project_id=sample_project.id,
                query_text="machine learning",
                user_id=sample_project.owner_id,
                top_k=5,
                use_hybrid_search=False,
                use_re_ranking=False,
            )
        
        # Assert
        assert isinstance(result, QueryKnowledgeResult)
        assert result.total_results == 3
        assert len(result.results) == 3
        
        # Verify results format: (item, similarity_score, bm25_score, rerank_score)
        item, sim_score, bm25_score, rerank_score = result.results[0]
        assert item.id == sample_knowledge_items[0].id
        assert sim_score == 0.95
        assert bm25_score is None
        assert rerank_score is None
        
        # Verify vector search was called
        mock_knowledge_repo.vector_search.assert_called_once()
        mock_knowledge_repo.keyword_search.assert_not_called()
        
        # Verify cache operations
        mock_cache_service.get.assert_called_once()
        mock_cache_service.set.assert_called_once()

    async def test_execute_hybrid_search_enabled(
        self,
        mock_knowledge_repo,
        mock_project_repo,
        mock_settings,
        mock_cache_service,
        sample_project,
        sample_knowledge_items,
    ):
        """Test hybrid search (vector + keyword) with RRF merge."""
        # Arrange
        mock_project_repo.get_by_id = AsyncMock(return_value=sample_project)
        mock_cache_service.get = AsyncMock(return_value=None)  # Cache miss
        
        # Mock vector search results
        vector_results = [
            (sample_knowledge_items[0], 0.95),
            (sample_knowledge_items[1], 0.85),
        ]
        mock_knowledge_repo.vector_search = AsyncMock(return_value=vector_results)
        
        # Mock keyword search results
        keyword_results = [
            (sample_knowledge_items[1], 12.5),  # Overlaps with vector
            (sample_knowledge_items[2], 8.3),   # Unique to keyword
        ]
        mock_knowledge_repo.keyword_search = AsyncMock(return_value=keyword_results)
        
        # Mock embedding provider
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_text = AsyncMock(return_value=[0.1] * 1536)
        
        use_case = QueryKnowledgeUseCase(
            knowledge_repo=mock_knowledge_repo,
            project_repo=mock_project_repo,
            settings=mock_settings,
            cache_service=mock_cache_service,
        )
        
        # Act
        with patch(
            "src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider",
            return_value=mock_embedding_provider,
        ):
            result = await use_case.execute(
                project_id=sample_project.id,
                query_text="machine learning neural networks",
                user_id=sample_project.owner_id,
                top_k=5,
                use_hybrid_search=True,
                use_re_ranking=False,
            )
        
        # Assert
        assert isinstance(result, QueryKnowledgeResult)
        assert result.total_results > 0
        
        # Verify both vector and keyword search were called
        mock_knowledge_repo.vector_search.assert_called_once()
        mock_knowledge_repo.keyword_search.assert_called_once()
        
        # Verify hybrid merge happened (results should be deduplicated)
        # Since item[1] appears in both searches, total should be 3 (not 4)
        assert result.total_results == 3

    async def test_execute_reranking_enabled(
        self,
        mock_knowledge_repo,
        mock_project_repo,
        mock_settings,
        mock_cache_service,
        sample_project,
        sample_knowledge_items,
    ):
        """Test LLM-based re-ranking of search results."""
        # Arrange
        mock_project_repo.get_by_id = AsyncMock(return_value=sample_project)
        mock_cache_service.get = AsyncMock(return_value=None)  # Cache miss
        
        # Mock vector search results
        vector_results = [
            (sample_knowledge_items[0], 0.95),
            (sample_knowledge_items[1], 0.85),
            (sample_knowledge_items[2], 0.75),
        ]
        mock_knowledge_repo.vector_search = AsyncMock(return_value=vector_results)
        
        # Mock embedding provider
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_text = AsyncMock(return_value=[0.1] * 1536)
        
        # Mock LLM provider for re-ranking
        mock_llm_provider = AsyncMock()
        mock_llm_provider.generate_completion = AsyncMock(
            return_value="[2, 0, 1]"  # Re-ranked order (indices)
        )
        
        use_case = QueryKnowledgeUseCase(
            knowledge_repo=mock_knowledge_repo,
            project_repo=mock_project_repo,
            settings=mock_settings,
            cache_service=mock_cache_service,
        )
        
        # Act
        with patch(
            "src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider",
            return_value=mock_embedding_provider,
        ), patch(
            "src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_llm_provider",
            return_value=mock_llm_provider,
        ):
            result = await use_case.execute(
                project_id=sample_project.id,
                query_text="natural language processing",
                user_id=sample_project.owner_id,
                top_k=5,
                use_hybrid_search=False,
                use_re_ranking=True,
            )
        
        # Assert
        assert isinstance(result, QueryKnowledgeResult)
        assert result.total_results == 3
        
        # Verify re-ranking was applied (order changed)
        item0, sim0, bm25_0, rerank0 = result.results[0]
        assert rerank0 is not None  # Re-rank score should be present
        assert rerank0 == 1.0  # Top result should have score 1.0
        
        # Verify LLM provider was called
        mock_llm_provider.generate_completion.assert_called_once()

    async def test_execute_hybrid_and_reranking_combined(
        self,
        mock_knowledge_repo,
        mock_project_repo,
        mock_settings,
        mock_cache_service,
        sample_project,
        sample_knowledge_items,
    ):
        """Test hybrid search + re-ranking together."""
        # Arrange
        mock_project_repo.get_by_id = AsyncMock(return_value=sample_project)
        mock_cache_service.get = AsyncMock(return_value=None)  # Cache miss
        
        # Mock vector and keyword search
        vector_results = [(sample_knowledge_items[0], 0.95)]
        keyword_results = [(sample_knowledge_items[1], 10.0)]
        mock_knowledge_repo.vector_search = AsyncMock(return_value=vector_results)
        mock_knowledge_repo.keyword_search = AsyncMock(return_value=keyword_results)
        
        # Mock embedding provider
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_text = AsyncMock(return_value=[0.1] * 1536)
        
        # Mock LLM provider for re-ranking
        mock_llm_provider = AsyncMock()
        mock_llm_provider.generate_completion = AsyncMock(return_value="[1, 0]")
        
        use_case = QueryKnowledgeUseCase(
            knowledge_repo=mock_knowledge_repo,
            project_repo=mock_project_repo,
            settings=mock_settings,
            cache_service=mock_cache_service,
        )
        
        # Act
        with patch(
            "src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider",
            return_value=mock_embedding_provider,
        ), patch(
            "src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_llm_provider",
            return_value=mock_llm_provider,
        ):
            result = await use_case.execute(
                project_id=sample_project.id,
                query_text="test query",
                user_id=sample_project.owner_id,
                use_hybrid_search=True,
                use_re_ranking=True,
            )
        
        # Assert
        assert isinstance(result, QueryKnowledgeResult)
        
        # Both vector and keyword search should be called
        mock_knowledge_repo.vector_search.assert_called_once()
        mock_knowledge_repo.keyword_search.assert_called_once()
        
        # Re-ranking should be applied
        mock_llm_provider.generate_completion.assert_called_once()

    async def test_execute_cache_hit(
        self,
        mock_knowledge_repo,
        mock_project_repo,
        mock_settings,
        mock_cache_service,
        sample_project,
        sample_knowledge_items,
    ):
        """Test cache hit scenario - should return cached results without database query."""
        # Arrange
        import json
        
        mock_project_repo.get_by_id = AsyncMock(return_value=sample_project)
        
        # Create cached data
        cached_data = json.dumps({
            "query_id": str(uuid4()),
            "results": [
                {
                    "id": str(sample_knowledge_items[0].id),
                    "document_id": str(sample_knowledge_items[0].document_id),
                    "chunk_text": sample_knowledge_items[0].chunk_text,
                    "chunk_index": 0,
                    "embedding": [0.1] * 1536,
                    "metadata": {"source": "test1"},
                    "created_at": datetime.utcnow().isoformat(),
                    "similarity_score": 0.95,
                    "bm25_score": None,
                    "rerank_score": None,
                }
            ],
            "total_results": 1,
        })
        
        mock_cache_service.get = AsyncMock(return_value=cached_data)
        
        use_case = QueryKnowledgeUseCase(
            knowledge_repo=mock_knowledge_repo,
            project_repo=mock_project_repo,
            settings=mock_settings,
            cache_service=mock_cache_service,
        )
        
        # Act
        result = await use_case.execute(
            project_id=sample_project.id,
            query_text="cached query",
            user_id=sample_project.owner_id,
        )
        
        # Assert
        assert isinstance(result, QueryKnowledgeResult)
        assert result.total_results == 1
        
        # Verify database was NOT queried (cache hit)
        mock_knowledge_repo.vector_search.assert_not_called()
        mock_knowledge_repo.keyword_search.assert_not_called()
        
        # Verify cache was checked
        mock_cache_service.get.assert_called_once()
        
        # Verify result was not cached again (already in cache)
        mock_cache_service.set.assert_not_called()

    async def test_execute_cache_disabled(
        self,
        mock_knowledge_repo,
        mock_project_repo,
        mock_settings,
        sample_project,
        sample_knowledge_items,
    ):
        """Test cache disabled scenario - no caching operations."""
        # Arrange
        mock_settings.rag.cache_enabled = False  # Disable cache
        mock_project_repo.get_by_id = AsyncMock(return_value=sample_project)
        
        vector_results = [(sample_knowledge_items[0], 0.95)]
        mock_knowledge_repo.vector_search = AsyncMock(return_value=vector_results)
        
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_text = AsyncMock(return_value=[0.1] * 1536)
        
        # Create cache service but it should not be used
        mock_cache_service = AsyncMock()
        
        use_case = QueryKnowledgeUseCase(
            knowledge_repo=mock_knowledge_repo,
            project_repo=mock_project_repo,
            settings=mock_settings,
            cache_service=mock_cache_service,
        )
        
        # Act
        with patch(
            "src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider",
            return_value=mock_embedding_provider,
        ):
            result = await use_case.execute(
                project_id=sample_project.id,
                query_text="test query",
                user_id=sample_project.owner_id,
            )
        
        # Assert
        assert isinstance(result, QueryKnowledgeResult)
        
        # Verify cache was NOT used (disabled)
        mock_cache_service.get.assert_not_called()
        mock_cache_service.set.assert_not_called()

    async def test_execute_configuration_defaults(
        self,
        mock_knowledge_repo,
        mock_project_repo,
        mock_settings,
        mock_cache_service,
        sample_project,
        sample_knowledge_items,
    ):
        """Test that settings defaults override request parameters."""
        # Arrange
        mock_settings.rag.use_hybrid_search = True  # Default enabled in settings
        mock_settings.rag.use_reranking = True      # Default enabled in settings
        
        mock_project_repo.get_by_id = AsyncMock(return_value=sample_project)
        mock_cache_service.get = AsyncMock(return_value=None)
        
        vector_results = [(sample_knowledge_items[0], 0.95)]
        keyword_results = [(sample_knowledge_items[1], 10.0)]
        mock_knowledge_repo.vector_search = AsyncMock(return_value=vector_results)
        mock_knowledge_repo.keyword_search = AsyncMock(return_value=keyword_results)
        
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_text = AsyncMock(return_value=[0.1] * 1536)
        
        mock_llm_provider = AsyncMock()
        mock_llm_provider.generate_completion = AsyncMock(return_value="[0, 1]")
        
        use_case = QueryKnowledgeUseCase(
            knowledge_repo=mock_knowledge_repo,
            project_repo=mock_project_repo,
            settings=mock_settings,
            cache_service=mock_cache_service,
        )
        
        # Act - Request with flags=False, but settings have defaults=True
        with patch(
            "src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_embedding_provider",
            return_value=mock_embedding_provider,
        ), patch(
            "src.application.use_cases.knowledge.query_knowledge.ProviderFactory.get_llm_provider",
            return_value=mock_llm_provider,
        ):
            result = await use_case.execute(
                project_id=sample_project.id,
                query_text="test query",
                user_id=sample_project.owner_id,
                use_hybrid_search=False,  # Request says False
                use_re_ranking=False,     # Request says False
            )
        
        # Assert - Settings defaults should override
        mock_knowledge_repo.keyword_search.assert_called_once()  # Hybrid enabled
        mock_llm_provider.generate_completion.assert_called_once()  # Re-ranking enabled

    async def test_execute_project_not_found(
        self,
        mock_knowledge_repo,
        mock_project_repo,
        mock_settings,
        mock_cache_service,
    ):
        """Test error handling when project doesn't exist."""
        # Arrange
        mock_project_repo.get_by_id = AsyncMock(return_value=None)
        
        use_case = QueryKnowledgeUseCase(
            knowledge_repo=mock_knowledge_repo,
            project_repo=mock_project_repo,
            settings=mock_settings,
            cache_service=mock_cache_service,
        )
        
        # Act & Assert
        with pytest.raises(ProjectNotFoundError):
            await use_case.execute(
                project_id=uuid4(),
                query_text="test query",
                user_id=uuid4(),
            )

    async def test_execute_unauthorized_access(
        self,
        mock_knowledge_repo,
        mock_project_repo,
        mock_settings,
        mock_cache_service,
        sample_project,
    ):
        """Test error handling when user doesn't own project."""
        # Arrange
        mock_project_repo.get_by_id = AsyncMock(return_value=sample_project)
        
        use_case = QueryKnowledgeUseCase(
            knowledge_repo=mock_knowledge_repo,
            project_repo=mock_project_repo,
            settings=mock_settings,
            cache_service=mock_cache_service,
        )
        
        # Act & Assert - Different user_id than project owner_id
        with pytest.raises(UnauthorizedAccessError):
            await use_case.execute(
                project_id=sample_project.id,
                query_text="test query",
                user_id=uuid4(),  # Different from sample_project.owner_id
            )
