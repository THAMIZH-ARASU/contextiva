"""Unit tests for RerankingService."""

import json
import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from datetime import datetime

from src.application.services.reranking_service import RerankingService
from src.domain.models.knowledge import KnowledgeItem


@pytest.fixture
def reranking_service():
    """Create RerankingService instance."""
    return RerankingService()


@pytest.fixture
def sample_chunks():
    """Create sample KnowledgeItem chunks."""
    base_time = datetime(2025, 11, 10, 12, 0, 0)
    
    chunks = []
    for i in range(5):
        chunk = KnowledgeItem(
            id=uuid4(),
            document_id=uuid4(),
            chunk_text=f"Sample chunk about topic {i}. This is chunk number {i}.",
            chunk_index=i,
            embedding=[0.1 * i] * 10,
            metadata={"index": i},
            created_at=base_time,
        )
        chunks.append(chunk)
    
    return chunks


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider."""
    provider = AsyncMock()
    return provider


@pytest.mark.asyncio
async def test_rerank_chunks_successful(reranking_service, sample_chunks, mock_llm_provider):
    """Test successful re-ranking with valid LLM response."""
    # Arrange
    query_text = "topic 2"
    mock_llm_provider.generate_completion.return_value = "[2, 1, 0, 3, 4]"
    
    # Act
    results = await reranking_service.rerank_chunks(
        query_text=query_text,
        chunks=sample_chunks,
        llm_provider=mock_llm_provider,
        top_k=5,
    )
    
    # Assert
    assert len(results) == 5
    # Check re-ranked order
    assert results[0][0].id == sample_chunks[2].id  # Index 2 ranked first
    assert results[1][0].id == sample_chunks[1].id  # Index 1 ranked second
    # Check scores are normalized
    assert results[0][1] == 1.0  # Top score
    assert abs(results[4][1] - 0.2) < 0.01  # Bottom score (1.0 - 4/5)


@pytest.mark.asyncio
async def test_rerank_chunks_empty_chunks(reranking_service, mock_llm_provider):
    """Test re-ranking with empty chunk list."""
    # Arrange
    query_text = "test query"
    
    # Act
    results = await reranking_service.rerank_chunks(
        query_text=query_text,
        chunks=[],
        llm_provider=mock_llm_provider,
        top_k=5,
    )
    
    # Assert
    assert len(results) == 0
    mock_llm_provider.generate_completion.assert_not_called()


@pytest.mark.asyncio
async def test_rerank_chunks_llm_failure(reranking_service, sample_chunks, mock_llm_provider):
    """Test fallback to original order when LLM fails."""
    # Arrange
    query_text = "test query"
    mock_llm_provider.generate_completion.side_effect = Exception("LLM API error")
    
    # Act
    results = await reranking_service.rerank_chunks(
        query_text=query_text,
        chunks=sample_chunks,
        llm_provider=mock_llm_provider,
        top_k=5,
    )
    
    # Assert
    assert len(results) == 5
    # Should return original order
    assert results[0][0].id == sample_chunks[0].id
    assert results[1][0].id == sample_chunks[1].id


@pytest.mark.asyncio
async def test_rerank_chunks_invalid_json(reranking_service, sample_chunks, mock_llm_provider):
    """Test fallback when LLM returns invalid JSON."""
    # Arrange
    query_text = "test query"
    mock_llm_provider.generate_completion.return_value = "not valid json"
    
    # Act
    results = await reranking_service.rerank_chunks(
        query_text=query_text,
        chunks=sample_chunks,
        llm_provider=mock_llm_provider,
        top_k=5,
    )
    
    # Assert
    assert len(results) == 5
    # Should return original order
    assert results[0][0].id == sample_chunks[0].id


@pytest.mark.asyncio
async def test_rerank_chunks_with_code_fences(reranking_service, sample_chunks, mock_llm_provider):
    """Test parsing LLM response with code fences."""
    # Arrange
    query_text = "test query"
    mock_llm_provider.generate_completion.return_value = "```json\n[4, 3, 2, 1, 0]\n```"
    
    # Act
    results = await reranking_service.rerank_chunks(
        query_text=query_text,
        chunks=sample_chunks,
        llm_provider=mock_llm_provider,
        top_k=5,
    )
    
    # Assert
    assert len(results) == 5
    assert results[0][0].id == sample_chunks[4].id  # Reverse order
    assert results[4][0].id == sample_chunks[0].id


@pytest.mark.asyncio
async def test_rerank_chunks_incomplete_ranking(reranking_service, sample_chunks, mock_llm_provider):
    """Test fallback when LLM returns incomplete ranking."""
    # Arrange
    query_text = "test query"
    # Missing indices - only 3 instead of 5
    mock_llm_provider.generate_completion.return_value = "[2, 1, 0]"
    
    # Act
    results = await reranking_service.rerank_chunks(
        query_text=query_text,
        chunks=sample_chunks,
        llm_provider=mock_llm_provider,
        top_k=5,
    )
    
    # Assert
    assert len(results) == 5
    # Should return original order due to validation failure
    assert results[0][0].id == sample_chunks[0].id


@pytest.mark.asyncio
async def test_rerank_chunks_top_k_limit(reranking_service, sample_chunks, mock_llm_provider):
    """Test that only top_k chunks are re-ranked."""
    # Arrange
    query_text = "test query"
    mock_llm_provider.generate_completion.return_value = "[2, 1, 0]"
    
    # Act
    results = await reranking_service.rerank_chunks(
        query_text=query_text,
        chunks=sample_chunks,
        llm_provider=mock_llm_provider,
        top_k=3,  # Only re-rank top 3
    )
    
    # Assert
    assert len(results) == 3
    assert results[0][0].id == sample_chunks[2].id
    assert results[1][0].id == sample_chunks[1].id
    assert results[2][0].id == sample_chunks[0].id
