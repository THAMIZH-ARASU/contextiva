"""PostgreSQL implementation of IKnowledgeRepository with pgvector support.

This module provides the concrete repository implementation for KnowledgeItem entities
using asyncpg, PostgreSQL, and pgvector for semantic search.
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from asyncpg import Pool

from src.domain.models.knowledge import IKnowledgeRepository, KnowledgeItem
from src.shared.utils.errors import KnowledgeItemNotFoundError


def _parse_pgvector(vector_str: str) -> list[float]:
    """Parse pgvector string representation to list of floats.
    
    Args:
        vector_str: String like "[0.1,0.2,0.3]"
    
    Returns:
        List of floats
    """
    # Remove brackets and split by comma
    cleaned = vector_str.strip('[]')
    if not cleaned:
        return []
    return [float(x.strip()) for x in cleaned.split(',')]


def _parse_metadata(metadata: Any) -> dict[str, Any]:
    """Parse metadata - handle both dict and JSON string.
    
    Args:
        metadata: Either a dict (already parsed) or JSON string
    
    Returns:
        Parsed metadata dictionary
    """
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str):
        return json.loads(metadata)
    return {}


class KnowledgeRepository(IKnowledgeRepository):
    """PostgreSQL implementation of knowledge repository with vector search."""

    def __init__(self, pool: Pool) -> None:
        """Initialize repository with database connection pool.
        
        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def create(self, item: KnowledgeItem) -> KnowledgeItem:
        """Create a new knowledge item in the database.
        
        Args:
            item: KnowledgeItem entity to create
            
        Returns:
            Created knowledge item with timestamp populated
        """
        query = """
            INSERT INTO knowledge_items (
                id, document_id, chunk_text, chunk_index, embedding, metadata, created_at
            )
            VALUES ($1, $2, $3, $4, $5::vector, $6::jsonb, $7)
            RETURNING id, document_id, chunk_text, chunk_index, embedding, metadata, created_at
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Convert embedding list to pgvector string format
        embedding_str = '[' + ','.join(str(x) for x in item.embedding) + ']'
        # Convert metadata dict to JSON string
        metadata_str = json.dumps(item.metadata)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                item.id,
                item.document_id,
                item.chunk_text,
                item.chunk_index,
                embedding_str,
                metadata_str,
                now,
            )

        if not row:
            raise RuntimeError("Failed to create knowledge item - no row returned")

        return KnowledgeItem(
            id=row["id"],
            document_id=row["document_id"],
            chunk_text=row["chunk_text"],
            chunk_index=row["chunk_index"],
            embedding=_parse_pgvector(row["embedding"]),
            metadata=_parse_metadata(row["metadata"]),
            created_at=row["created_at"],
        )

    async def create_batch(self, items: list[KnowledgeItem]) -> list[KnowledgeItem]:
        """Create multiple knowledge items in a batch.
        
        Args:
            items: List of KnowledgeItem entities to create
            
        Returns:
            List of created knowledge items
        """
        if not items:
            return []

        query = """
            INSERT INTO knowledge_items (
                id, document_id, chunk_text, chunk_index, embedding, metadata, created_at
            )
            VALUES ($1, $2, $3, $4, $5::vector, $6::jsonb, $7)
            RETURNING id, document_id, chunk_text, chunk_index, embedding, metadata, created_at
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        async with self.pool.acquire() as conn:
            # Execute batch insert
            results = []
            async with conn.transaction():
                for item in items:
                    # Convert embedding list to pgvector string format
                    embedding_str = '[' + ','.join(str(x) for x in item.embedding) + ']'
                    # Convert metadata dict to JSON string
                    metadata_str = json.dumps(item.metadata)
                    row = await conn.fetchrow(
                        query,
                        item.id,
                        item.document_id,
                        item.chunk_text,
                        item.chunk_index,
                        embedding_str,
                        metadata_str,
                        now,
                    )
                    if row:
                        results.append(
                            KnowledgeItem(
                                id=row["id"],
                                document_id=row["document_id"],
                                chunk_text=row["chunk_text"],
                                chunk_index=row["chunk_index"],
                                embedding=_parse_pgvector(row["embedding"]),
                                metadata=_parse_metadata(row["metadata"]),
                                created_at=row["created_at"],
                            )
                        )

        return results

    async def get_by_id(self, item_id: UUID) -> Optional[KnowledgeItem]:
        """Retrieve a knowledge item by ID.
        
        Args:
            item_id: Knowledge item identifier
            
        Returns:
            KnowledgeItem if found, None otherwise
        """
        query = """
            SELECT id, document_id, chunk_text, chunk_index, embedding, metadata, created_at
            FROM knowledge_items
            WHERE id = $1
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, item_id)

        if not row:
            return None

        return KnowledgeItem(
            id=row["id"],
            document_id=row["document_id"],
            chunk_text=row["chunk_text"],
            chunk_index=row["chunk_index"],
            embedding=_parse_pgvector(row["embedding"]),
            metadata=_parse_metadata(row["metadata"]),
            created_at=row["created_at"],
        )

    async def get_by_document(
        self, document_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[KnowledgeItem]:
        """Retrieve all knowledge items for a document.
        
        Args:
            document_id: Document identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of knowledge items for the document, ordered by chunk_index
        """
        query = """
            SELECT id, document_id, chunk_text, chunk_index, embedding, metadata, created_at
            FROM knowledge_items
            WHERE document_id = $1
            ORDER BY chunk_index ASC
            LIMIT $2 OFFSET $3
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, document_id, limit, skip)

        return [
            KnowledgeItem(
                id=row["id"],
                document_id=row["document_id"],
                chunk_text=row["chunk_text"],
                chunk_index=row["chunk_index"],
                embedding=_parse_pgvector(row["embedding"]),
                metadata=_parse_metadata(row["metadata"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def search_similar(
        self,
        embedding: list[float],
        limit: int = 10,
        project_id: Optional[UUID] = None,
        similarity_threshold: float = 0.7,
    ) -> list[tuple[KnowledgeItem, float]]:
        """Search for similar knowledge items using vector similarity.
        
        Args:
            embedding: Query embedding vector
            limit: Maximum number of results to return
            project_id: Optional project ID to filter results
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of tuples (KnowledgeItem, similarity_score) ordered by similarity
        """
        # Convert embedding list to pgvector string format
        embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
        
        # Use cosine similarity (1 - cosine_distance)
        if project_id:
            query = """
                SELECT k.id, k.document_id, k.chunk_text, k.chunk_index, 
                       k.embedding, k.metadata, k.created_at,
                       1 - (k.embedding <=> $1::vector) as similarity
                FROM knowledge_items k
                JOIN documents d ON k.document_id = d.id
                WHERE d.project_id = $2
                  AND 1 - (k.embedding <=> $1::vector) >= $3
                ORDER BY k.embedding <=> $1::vector
                LIMIT $4
            """
            params = [embedding_str, project_id, similarity_threshold, limit]
        else:
            query = """
                SELECT id, document_id, chunk_text, chunk_index, 
                       embedding, metadata, created_at,
                       1 - (embedding <=> $1::vector) as similarity
                FROM knowledge_items
                WHERE 1 - (embedding <=> $1::vector) >= $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """
            params = [embedding_str, similarity_threshold, limit]

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            (
                KnowledgeItem(
                    id=row["id"],
                    document_id=row["document_id"],
                    chunk_text=row["chunk_text"],
                    chunk_index=row["chunk_index"],
                    embedding=_parse_pgvector(row["embedding"]),
                    metadata=_parse_metadata(row["metadata"]),
                    created_at=row["created_at"],
                ),
                float(row["similarity"]),
            )
            for row in rows
        ]

    async def vector_search(
        self, project_id: UUID, query_embedding: list[float], top_k: int
    ) -> list[tuple[KnowledgeItem, float]]:
        """Perform vector similarity search against knowledge items filtered by project.
        
        Args:
            project_id: UUID of the project to filter results by
            query_embedding: Query embedding vector
            top_k: Maximum number of results to return
            
        Returns:
            List of tuples (KnowledgeItem, similarity_score) ordered by similarity (highest first)
        """
        # Convert embedding list to pgvector string format
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
        
        # Use cosine distance operator (<->) - lower distance = more similar
        # Convert to similarity score: 1 - cosine_distance
        query = """
            SELECT ki.id, ki.document_id, ki.chunk_text, ki.chunk_index, 
                   ki.embedding, ki.metadata, ki.created_at,
                   1 - (ki.embedding <=> $1::vector) as similarity_score
            FROM knowledge_items ki
            JOIN documents d ON ki.document_id = d.id
            WHERE d.project_id = $2
            ORDER BY ki.embedding <=> $1::vector ASC
            LIMIT $3
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, embedding_str, project_id, top_k)

        return [
            (
                KnowledgeItem(
                    id=row["id"],
                    document_id=row["document_id"],
                    chunk_text=row["chunk_text"],
                    chunk_index=row["chunk_index"],
                    embedding=_parse_pgvector(row["embedding"]),
                    metadata=_parse_metadata(row["metadata"]),
                    created_at=row["created_at"],
                ),
                float(row["similarity_score"]),
            )
            for row in rows
        ]

    async def keyword_search(
        self, project_id: UUID, query_text: str, top_k: int
    ) -> list[tuple[KnowledgeItem, float]]:
        """Perform keyword/BM25 full-text search against knowledge items filtered by project.
        
        Args:
            project_id: UUID of the project to filter results by
            query_text: Query text for full-text search
            top_k: Maximum number of results to return
            
        Returns:
            List of tuples (KnowledgeItem, bm25_score) ordered by relevance (highest first)
        """
        # Use PostgreSQL's ts_rank_cd() for BM25-like scoring
        # to_tsvector() converts text to searchable document
        # to_tsquery() converts query to search query (handles multiple words)
        # plainto_tsquery is more forgiving - handles natural language queries
        query = """
            SELECT ki.id, ki.document_id, ki.chunk_text, ki.chunk_index, 
                   ki.embedding, ki.metadata, ki.created_at,
                   ts_rank_cd(to_tsvector('english', ki.chunk_text), 
                              plainto_tsquery('english', $1)) as bm25_score
            FROM knowledge_items ki
            JOIN documents d ON ki.document_id = d.id
            WHERE d.project_id = $2
              AND to_tsvector('english', ki.chunk_text) @@ plainto_tsquery('english', $1)
            ORDER BY bm25_score DESC
            LIMIT $3
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, query_text, project_id, top_k)

        # Return empty list if no matches (rather than error)
        if not rows:
            return []

        return [
            (
                KnowledgeItem(
                    id=row["id"],
                    document_id=row["document_id"],
                    chunk_text=row["chunk_text"],
                    chunk_index=row["chunk_index"],
                    embedding=_parse_pgvector(row["embedding"]),
                    metadata=_parse_metadata(row["metadata"]),
                    created_at=row["created_at"],
                ),
                float(row["bm25_score"]),
            )
            for row in rows
        ]

    async def delete(self, item_id: UUID) -> bool:
        """Delete a knowledge item by ID.
        
        Args:
            item_id: Knowledge item identifier
            
        Returns:
            True if deleted, False if not found
        """
        query = "DELETE FROM knowledge_items WHERE id = $1"

        async with self.pool.acquire() as conn:
            result = await conn.execute(query, item_id)

        # Result is like "DELETE 1" or "DELETE 0"
        return result.endswith("1")

    async def delete_by_document(self, document_id: UUID) -> int:
        """Delete all knowledge items for a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Number of knowledge items deleted
        """
        query = "DELETE FROM knowledge_items WHERE document_id = $1"

        async with self.pool.acquire() as conn:
            result = await conn.execute(query, document_id)

        # Result is like "DELETE 5" - extract the number
        return int(result.split()[-1])
