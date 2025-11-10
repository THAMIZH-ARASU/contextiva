"""Hybrid search service for merging vector and keyword search results.

This service implements the Reciprocal Rank Fusion (RRF) algorithm to combine
vector similarity search and keyword/BM25 search results.
"""

from typing import Any
from uuid import UUID

from src.domain.models.knowledge import KnowledgeItem


class HybridSearchService:
    """Service for merging vector and keyword search results using RRF."""

    async def merge_results(
        self,
        vector_results: list[tuple[KnowledgeItem, float]],
        keyword_results: list[tuple[KnowledgeItem, float]],
        weight_vector: float,
        weight_bm25: float,
    ) -> list[tuple[KnowledgeItem, float]]:
        """Merge vector and keyword search results using Reciprocal Rank Fusion.
        
        Uses the RRF algorithm with configurable weights:
        score = weight_vector * (1 / (rank_vector + 60)) + weight_bm25 * (1 / (rank_bm25 + 60))
        
        Args:
            vector_results: List of (KnowledgeItem, similarity_score) from vector search
            keyword_results: List of (KnowledgeItem, bm25_score) from keyword search
            weight_vector: Weight for vector search results (typically 0.7)
            weight_bm25: Weight for keyword search results (typically 0.3)
            
        Returns:
            Merged list of (KnowledgeItem, combined_score) sorted by score (descending)
        """
        # Build rank maps: item_id -> rank (0-based)
        vector_ranks: dict[UUID, int] = {
            item.id: rank for rank, (item, _) in enumerate(vector_results)
        }
        keyword_ranks: dict[UUID, int] = {
            item.id: rank for rank, (item, _) in enumerate(keyword_results)
        }

        # Build item map for deduplication
        items_by_id: dict[UUID, KnowledgeItem] = {}
        for item, _ in vector_results:
            items_by_id[item.id] = item
        for item, _ in keyword_results:
            if item.id not in items_by_id:
                items_by_id[item.id] = item

        # Calculate RRF scores
        rrf_scores: dict[UUID, float] = {}
        k = 60  # Standard RRF constant

        for item_id in items_by_id:
            score = 0.0
            
            # Add vector search contribution if present
            if item_id in vector_ranks:
                score += weight_vector * (1.0 / (vector_ranks[item_id] + k))
            
            # Add keyword search contribution if present
            if item_id in keyword_ranks:
                score += weight_bm25 * (1.0 / (keyword_ranks[item_id] + k))
            
            rrf_scores[item_id] = score

        # Sort by combined score (descending)
        sorted_items = sorted(
            rrf_scores.items(), key=lambda x: x[1], reverse=True
        )

        # Build result list
        return [
            (items_by_id[item_id], score) for item_id, score in sorted_items
        ]
