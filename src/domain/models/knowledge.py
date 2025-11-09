"""KnowledgeItem domain model and repository interface.

This module defines the KnowledgeItem entity for storing document chunks
with vector embeddings for semantic search and retrieval.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID


@dataclass(slots=True)
class KnowledgeItem:
    """KnowledgeItem entity representing a chunked document with embedding.
    
    Attributes:
        id: Unique identifier for the knowledge item
        document_id: Foreign key to the parent document
        chunk_text: The actual text content of this chunk
        chunk_index: 0-based index of this chunk in the document
        embedding: Vector embedding of the chunk (list of floats)
        metadata: Additional metadata as JSON-serializable dict
        created_at: Timestamp when item was created
    """

    id: UUID
    document_id: UUID
    chunk_text: str
    chunk_index: int
    embedding: list[float]
    metadata: dict[str, Any]
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate knowledge item attributes after initialization."""
        # Validate chunk_text is not empty
        if not self.chunk_text or not self.chunk_text.strip():
            raise ValueError("Chunk text cannot be empty")

        # Validate chunk_index is non-negative
        if self.chunk_index < 0:
            raise ValueError(
                f"Chunk index must be non-negative, got: {self.chunk_index}"
            )

        # Validate embedding is a list of floats
        if not isinstance(self.embedding, list):
            raise ValueError("Embedding must be a list of floats")

        if not self.embedding:
            raise ValueError("Embedding cannot be empty")

        if not all(isinstance(val, (int, float)) for val in self.embedding):
            raise ValueError("All embedding values must be numeric")

        # Validate metadata is a dict
        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")


class IKnowledgeRepository(ABC):
    """Repository interface for KnowledgeItem entity operations."""

    @abstractmethod
    async def create(self, item: KnowledgeItem) -> KnowledgeItem:
        """Create a new knowledge item.
        
        Args:
            item: KnowledgeItem entity to create
            
        Returns:
            Created knowledge item with generated fields populated
            
        Raises:
            ValueError: If knowledge item validation fails
        """
        pass

    @abstractmethod
    async def create_batch(self, items: list[KnowledgeItem]) -> list[KnowledgeItem]:
        """Create multiple knowledge items in a batch.
        
        Args:
            items: List of KnowledgeItem entities to create
            
        Returns:
            List of created knowledge items
            
        Raises:
            ValueError: If any knowledge item validation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, item_id: UUID) -> Optional[KnowledgeItem]:
        """Retrieve a knowledge item by its ID.
        
        Args:
            item_id: Unique identifier of the knowledge item
            
        Returns:
            KnowledgeItem if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_document(
        self, document_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[KnowledgeItem]:
        """Retrieve all knowledge items for a document.
        
        Args:
            document_id: ID of the parent document
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of knowledge items for the document, ordered by chunk_index
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def vector_search(
        self, project_id: UUID, query_embedding: list[float], top_k: int
    ) -> list[tuple[KnowledgeItem, float]]:
        """Perform vector similarity search against knowledge items.
        
        Args:
            project_id: UUID of the project to filter results by
            query_embedding: Query embedding vector
            top_k: Maximum number of results to return
            
        Returns:
            List of tuples (KnowledgeItem, similarity_score) ordered by similarity (highest first)
        """
        pass

    @abstractmethod
    async def delete(self, item_id: UUID) -> bool:
        """Delete a knowledge item by ID.
        
        Args:
            item_id: Unique identifier of the knowledge item
            
        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def delete_by_document(self, document_id: UUID) -> int:
        """Delete all knowledge items for a document.
        
        Args:
            document_id: ID of the parent document
            
        Returns:
            Number of knowledge items deleted
        """
        pass
