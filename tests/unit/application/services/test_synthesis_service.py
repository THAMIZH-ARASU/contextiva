"""Unit tests for SynthesisService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.synthesis_service import SynthesisService
from src.domain.models.knowledge import KnowledgeItem
from src.shared.config.settings import RAGSettings


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    provider = AsyncMock()
    provider.generate_completion = AsyncMock()
    return provider


@pytest.fixture
def mock_settings():
    """Mock RAG settings."""
    return RAGSettings(
        default_top_k=5,
        max_top_k=50,
        use_hybrid_search=False,
        hybrid_search_weight_vector=0.7,
        hybrid_search_weight_bm25=0.3,
        use_reranking=False,
        reranking_model="stable-code:3b-code-q5_K_M",
        reranking_top_k=10,
        cache_enabled=False,
        cache_ttl=3600,
        cache_key_prefix="rag:query:",
        use_agentic_rag=True,
        agentic_rag_model="stable-code:3b-code-q5_K_M",
        agentic_rag_max_tokens=1000,
        agentic_rag_temperature=0.3,
        agentic_rag_system_prompt="You are a helpful assistant.",
    )


@pytest.fixture
def sample_chunks():
    """Sample knowledge items for testing."""
    return [
        KnowledgeItem(
            id=uuid4(),
            document_id=uuid4(),
            chunk_text="Python is a high-level programming language.",
            chunk_index=0,
            embedding=[0.1] * 1536,
            metadata={"page": 1},
            created_at=datetime.now(),
        ),
        KnowledgeItem(
            id=uuid4(),
            document_id=uuid4(),
            chunk_text="FastAPI is a modern web framework for Python.",
            chunk_index=1,
            embedding=[0.2] * 1536,
            metadata={"page": 2},
            created_at=datetime.now(),
        ),
    ]


@pytest.mark.asyncio
async def test_synthesize_success(mock_llm_provider, mock_settings, sample_chunks):
    """Test successful synthesis with valid inputs."""
    # Arrange
    service = SynthesisService()
    query = "What is Python?"
    expected_answer = "Python is a high-level programming language used for various applications."
    mock_llm_provider.generate_completion.return_value = expected_answer

    # Act
    result = await service.synthesize(
        query=query,
        chunks=sample_chunks,
        llm_provider=mock_llm_provider,
        settings=mock_settings,
    )

    # Assert
    assert result == expected_answer
    mock_llm_provider.generate_completion.assert_called_once()
    call_kwargs = mock_llm_provider.generate_completion.call_args.kwargs
    assert call_kwargs["model"] == mock_settings.agentic_rag_model
    assert call_kwargs["max_tokens"] == mock_settings.agentic_rag_max_tokens
    assert call_kwargs["temperature"] == mock_settings.agentic_rag_temperature
    
    # Verify messages structure
    messages = call_kwargs["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == mock_settings.agentic_rag_system_prompt
    assert messages[1]["role"] == "user"
    assert query in messages[1]["content"]
    assert sample_chunks[0].chunk_text in messages[1]["content"]
    assert sample_chunks[1].chunk_text in messages[1]["content"]


@pytest.mark.asyncio
async def test_synthesize_empty_chunks(mock_llm_provider, mock_settings):
    """Test synthesis with empty chunks list returns None."""
    # Arrange
    service = SynthesisService()
    query = "What is Python?"

    # Act
    result = await service.synthesize(
        query=query,
        chunks=[],
        llm_provider=mock_llm_provider,
        settings=mock_settings,
    )

    # Assert
    assert result is None
    mock_llm_provider.generate_completion.assert_not_called()


@pytest.mark.asyncio
async def test_synthesize_single_chunk(mock_llm_provider, mock_settings, sample_chunks):
    """Test synthesis with single chunk."""
    # Arrange
    service = SynthesisService()
    query = "What is Python?"
    single_chunk = [sample_chunks[0]]
    expected_answer = "Python is a programming language."
    mock_llm_provider.generate_completion.return_value = expected_answer

    # Act
    result = await service.synthesize(
        query=query,
        chunks=single_chunk,
        llm_provider=mock_llm_provider,
        settings=mock_settings,
    )

    # Assert
    assert result == expected_answer
    mock_llm_provider.generate_completion.assert_called_once()


@pytest.mark.asyncio
async def test_synthesize_llm_failure_graceful_degradation(mock_llm_provider, mock_settings, sample_chunks):
    """Test LLM provider failure returns None (graceful degradation)."""
    # Arrange
    service = SynthesisService()
    query = "What is Python?"
    mock_llm_provider.generate_completion.side_effect = Exception("LLM API error")

    # Act
    result = await service.synthesize(
        query=query,
        chunks=sample_chunks,
        llm_provider=mock_llm_provider,
        settings=mock_settings,
    )

    # Assert
    assert result is None  # Graceful degradation
    mock_llm_provider.generate_completion.assert_called_once()


@pytest.mark.asyncio
async def test_synthesize_prompt_construction(mock_llm_provider, mock_settings, sample_chunks):
    """Test that prompt includes query and all chunks."""
    # Arrange
    service = SynthesisService()
    query = "Tell me about Python and FastAPI"
    mock_llm_provider.generate_completion.return_value = "Answer"

    # Act
    await service.synthesize(
        query=query,
        chunks=sample_chunks,
        llm_provider=mock_llm_provider,
        settings=mock_settings,
    )

    # Assert
    messages = mock_llm_provider.generate_completion.call_args.kwargs["messages"]
    user_message = messages[1]["content"]
    
    # Verify query is in prompt
    assert query in user_message
    
    # Verify all chunks are in prompt
    for chunk in sample_chunks:
        assert chunk.chunk_text in user_message
    
    # Verify chunk numbering
    assert "[Chunk 1]" in user_message
    assert "[Chunk 2]" in user_message


@pytest.mark.asyncio
async def test_synthesize_settings_passed_to_llm(mock_llm_provider, mock_settings, sample_chunks):
    """Test that max_tokens and temperature settings are passed to LLM."""
    # Arrange
    service = SynthesisService()
    query = "What is Python?"
    mock_llm_provider.generate_completion.return_value = "Answer"

    # Act
    await service.synthesize(
        query=query,
        chunks=sample_chunks,
        llm_provider=mock_llm_provider,
        settings=mock_settings,
    )

    # Assert
    call_kwargs = mock_llm_provider.generate_completion.call_args.kwargs
    assert call_kwargs["model"] == mock_settings.agentic_rag_model
    assert call_kwargs["max_tokens"] == 1000
    assert call_kwargs["temperature"] == 0.3


@pytest.mark.asyncio
async def test_synthesize_strips_whitespace(mock_llm_provider, mock_settings, sample_chunks):
    """Test that synthesized answer has leading/trailing whitespace stripped."""
    # Arrange
    service = SynthesisService()
    query = "What is Python?"
    answer_with_whitespace = "  \n  Python is a language.  \n  "
    mock_llm_provider.generate_completion.return_value = answer_with_whitespace

    # Act
    result = await service.synthesize(
        query=query,
        chunks=sample_chunks,
        llm_provider=mock_llm_provider,
        settings=mock_settings,
    )

    # Assert
    assert result == "Python is a language."
    assert not result.startswith(" ")
    assert not result.endswith(" ")
