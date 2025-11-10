"""Re-ranking service for LLM-based chunk re-ranking.

This service uses an LLM provider to re-rank retrieved chunks based on
their relevance to the original query.
"""

import json
import logging
from typing import Any

from src.domain.models.knowledge import KnowledgeItem
from src.infrastructure.external.llm.providers.base import ILLMProvider

logger = logging.getLogger(__name__)


class RerankingService:
    """Service for re-ranking chunks using LLM provider."""

    async def rerank_chunks(
        self,
        query_text: str,
        chunks: list[KnowledgeItem],
        llm_provider: ILLMProvider,
        top_k: int,
    ) -> list[tuple[KnowledgeItem, float]]:
        """Re-rank chunks using LLM to determine relevance to query.

        Constructs a prompt asking the LLM to rank chunks by relevance,
        parses the response, and returns chunks in re-ranked order with scores.

        Args:
            query_text: The original query text
            chunks: List of KnowledgeItem entities to re-rank
            llm_provider: LLM provider instance for re-ranking
            top_k: Number of top results to return after re-ranking

        Returns:
            List of (KnowledgeItem, rerank_score) in re-ranked order with normalized scores

        Note:
            If LLM fails or returns invalid response, returns original order with warning log.
        """
        if not chunks:
            return []

        # Limit to top_k chunks for re-ranking to reduce cost
        chunks_to_rerank = chunks[:top_k]

        # Build re-ranking prompt
        prompt = self._build_reranking_prompt(query_text, chunks_to_rerank)

        try:
            # Call LLM provider
            response = await llm_provider.generate_completion(
                prompt=prompt,
                max_tokens=500,
                temperature=0.0,  # Deterministic re-ranking
            )

            # Parse response as JSON array of indices
            ranked_indices = self._parse_llm_response(response)

            # Validate indices
            if not self._validate_indices(ranked_indices, len(chunks_to_rerank)):
                logger.warning(
                    "LLM re-ranking returned invalid indices, using original order"
                )
                return self._original_order_with_scores(chunks_to_rerank)

            # Build re-ranked results with normalized scores
            return self._build_reranked_results(chunks_to_rerank, ranked_indices)

        except Exception as e:
            logger.warning(
                f"LLM re-ranking failed with error: {e}, using original order"
            )
            return self._original_order_with_scores(chunks_to_rerank)

    def _build_reranking_prompt(
        self, query_text: str, chunks: list[KnowledgeItem]
    ) -> str:
        """Build prompt for LLM re-ranking.

        Args:
            query_text: The original query
            chunks: Chunks to re-rank

        Returns:
            Formatted prompt string
        """
        chunks_text = "\n".join(
            [f"{i}: {chunk.chunk_text[:200]}..." for i, chunk in enumerate(chunks)]
        )

        prompt = f"""Given the query: '{query_text}', rank the following text chunks by relevance (most relevant first).
Return ONLY a JSON array of indices (0-based) representing the ranking, from most to least relevant.

Example output: [2, 0, 4, 1, 3]

Chunks:
{chunks_text}

Your ranking (JSON array only):"""

        return prompt

    def _parse_llm_response(self, response: str) -> list[int]:
        """Parse LLM response as JSON array of integers.

        Args:
            response: Raw LLM response text

        Returns:
            List of integer indices

        Raises:
            ValueError: If response is not valid JSON array
        """
        # Try to extract JSON array from response
        response = response.strip()

        # Handle common LLM response patterns
        if response.startswith("```"):
            # Extract content between code fences
            lines = response.split("\n")
            for line in lines:
                if line.strip() and not line.startswith("```"):
                    response = line.strip()
                    break

        # Parse as JSON
        try:
            indices = json.loads(response)
            if not isinstance(indices, list):
                raise ValueError("Response is not a JSON array")
            return [int(idx) for idx in indices]
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response as JSON: {response}")
            raise ValueError(f"Invalid JSON response: {e}")

    def _validate_indices(self, indices: list[int], expected_count: int) -> bool:
        """Validate that indices are valid and complete.

        Args:
            indices: List of indices from LLM
            expected_count: Expected number of chunks

        Returns:
            True if indices are valid, False otherwise
        """
        if len(indices) != expected_count:
            return False

        # Check all indices are in valid range and unique
        if set(indices) != set(range(expected_count)):
            return False

        return True

    def _build_reranked_results(
        self, chunks: list[KnowledgeItem], ranked_indices: list[int]
    ) -> list[tuple[KnowledgeItem, float]]:
        """Build re-ranked results with normalized scores.

        Args:
            chunks: Original chunks
            ranked_indices: Indices in re-ranked order

        Returns:
            List of (KnowledgeItem, score) tuples
        """
        results = []
        num_chunks = len(ranked_indices)

        for rank, idx in enumerate(ranked_indices):
            # Normalized score: 1.0 for top, decreasing linearly
            score = 1.0 - (rank / num_chunks)
            results.append((chunks[idx], score))

        return results

    def _original_order_with_scores(
        self, chunks: list[KnowledgeItem]
    ) -> list[tuple[KnowledgeItem, float]]:
        """Return chunks in original order with default scores.

        Args:
            chunks: Original chunks

        Returns:
            List of (KnowledgeItem, score) tuples in original order
        """
        num_chunks = len(chunks)
        return [
            (chunk, 1.0 - (i / num_chunks)) for i, chunk in enumerate(chunks)
        ]
