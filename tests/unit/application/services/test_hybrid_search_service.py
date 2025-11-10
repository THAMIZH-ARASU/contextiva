"""Unit tests for HybridSearchService."""

import pytest
from uuid import uuid4
from datetime import datetime

from src.application.services.hybrid_search_service import HybridSearchService
from src.domain.models.knowledge import KnowledgeItem


@pytest.fixture
def hybrid_service():
    """Create HybridSearchService instance."""
    return HybridSearchService()


@pytest.fixture
def sample_items():
    """Create sample KnowledgeItem instances for testing."""
    base_time = datetime(2025, 11, 10, 12, 0, 0)
    
    items = []
    for i in range(5):
        item = KnowledgeItem(
            id=uuid4(),
            document_id=uuid4(),
            chunk_text=f"Sample chunk text {i}",
            chunk_index=i,
            embedding=[0.1 * i] * 10,
            metadata={"index": i},
            created_at=base_time,
        )
        items.append(item)
    
    return items


@pytest.mark.asyncio
async def test_merge_results_vector_only(hybrid_service, sample_items):
    """Test merging when only vector results exist."""
    # Arrange
    vector_results = [(sample_items[0], 0.9), (sample_items[1], 0.8)]
    keyword_results = []
    
    # Act
    merged = await hybrid_service.merge_results(
        vector_results=vector_results,
        keyword_results=keyword_results,
        weight_vector=0.7,
        weight_bm25=0.3,
    )
    
    # Assert
    assert len(merged) == 2
    assert merged[0][0].id == sample_items[0].id
    assert merged[1][0].id == sample_items[1].id


@pytest.mark.asyncio
async def test_merge_results_keyword_only(hybrid_service, sample_items):
    """Test merging when only keyword results exist."""
    # Arrange
    vector_results = []
    keyword_results = [(sample_items[2], 5.0), (sample_items[3], 3.0)]
    
    # Act
    merged = await hybrid_service.merge_results(
        vector_results=vector_results,
        keyword_results=keyword_results,
        weight_vector=0.7,
        weight_bm25=0.3,
    )
    
    # Assert
    assert len(merged) == 2
    assert merged[0][0].id == sample_items[2].id
    assert merged[1][0].id == sample_items[3].id


@pytest.mark.asyncio
async def test_merge_results_deduplication(hybrid_service, sample_items):
    """Test that duplicate items are deduplicated with highest score kept."""
    # Arrange - same item appears in both results
    vector_results = [(sample_items[0], 0.9), (sample_items[1], 0.7)]
    keyword_results = [(sample_items[0], 10.0), (sample_items[2], 5.0)]
    
    # Act
    merged = await hybrid_service.merge_results(
        vector_results=vector_results,
        keyword_results=keyword_results,
        weight_vector=0.7,
        weight_bm25=0.3,
    )
    
    # Assert
    assert len(merged) == 3  # Deduplicated: items 0, 1, 2
    ids = [item.id for item, _ in merged]
    assert sample_items[0].id in ids
    assert sample_items[1].id in ids
    assert sample_items[2].id in ids


@pytest.mark.asyncio
async def test_merge_results_rrf_scoring(hybrid_service, sample_items):
    """Test RRF scoring formula is applied correctly."""
    # Arrange
    vector_results = [(sample_items[0], 0.9)]  # Rank 0 in vector
    keyword_results = [(sample_items[0], 5.0)]  # Rank 0 in keyword
    
    # Act
    merged = await hybrid_service.merge_results(
        vector_results=vector_results,
        keyword_results=keyword_results,
        weight_vector=0.7,
        weight_bm25=0.3,
    )
    
    # Assert
    assert len(merged) == 1
    # RRF score = 0.7 * (1/(0+60)) + 0.3 * (1/(0+60)) = 1.0 * (1/60) = 0.0167
    expected_score = 0.7 * (1.0 / 60) + 0.3 * (1.0 / 60)
    assert abs(merged[0][1] - expected_score) < 0.0001


@pytest.mark.asyncio
async def test_merge_results_empty_both(hybrid_service):
    """Test merging with no results."""
    # Arrange
    vector_results = []
    keyword_results = []
    
    # Act
    merged = await hybrid_service.merge_results(
        vector_results=vector_results,
        keyword_results=keyword_results,
        weight_vector=0.7,
        weight_bm25=0.3,
    )
    
    # Assert
    assert len(merged) == 0


@pytest.mark.asyncio
async def test_merge_results_sorted_by_score(hybrid_service, sample_items):
    """Test that results are sorted by combined score (descending)."""
    # Arrange - set up so we know the ranking
    vector_results = [(sample_items[0], 0.9), (sample_items[1], 0.8), (sample_items[2], 0.7)]
    keyword_results = [(sample_items[1], 10.0), (sample_items[2], 5.0), (sample_items[0], 3.0)]
    
    # Act
    merged = await hybrid_service.merge_results(
        vector_results=vector_results,
        keyword_results=keyword_results,
        weight_vector=0.7,
        weight_bm25=0.3,
    )
    
    # Assert
    assert len(merged) == 3
    # Verify descending order
    scores = [score for _, score in merged]
    assert scores == sorted(scores, reverse=True)
