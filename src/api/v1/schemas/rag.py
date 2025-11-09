"""Pydantic schemas for RAG (Retrieval-Augmented Generation) endpoints."""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    """Request schema for RAG query endpoint.
    
    Attributes:
        project_id: UUID of the project to query against.
        query_text: The text query to search for (1-10000 characters).
        top_k: Optional number of results to return (uses settings default if not provided).
    """

    project_id: UUID = Field(..., description="UUID of the project to query against")
    query_text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The text query to search for"
    )
    top_k: Optional[int] = Field(
        None,
        description="Number of results to return (uses settings default if not provided)",
        gt=0
    )


class KnowledgeItemResult(BaseModel):
    """Individual knowledge item result from RAG query.
    
    Attributes:
        id: UUID of the knowledge item.
        chunk_text: The text content of the chunk.
        similarity_score: Cosine similarity score (0-1, higher is more similar).
        metadata: Optional metadata (page number, source URL, chunk indices, etc.).
        document_id: UUID of the parent document.
    """

    id: UUID = Field(..., description="UUID of the knowledge item")
    chunk_text: str = Field(..., description="The text content of the chunk")
    similarity_score: float = Field(
        ...,
        description="Cosine similarity score (0-1, higher is more similar)",
        ge=0.0,
        le=1.0
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Optional metadata (page number, source URL, chunk indices, etc.)"
    )
    document_id: UUID = Field(..., description="UUID of the parent document")


class RAGQueryResponse(BaseModel):
    """Response schema for RAG query endpoint.
    
    Attributes:
        results: List of matching knowledge items ordered by similarity.
        query_id: UUID identifier for this query (for tracking/debugging).
        total_results: Total number of results returned.
    """

    results: list[KnowledgeItemResult] = Field(
        ...,
        description="List of matching knowledge items ordered by similarity"
    )
    query_id: UUID = Field(
        ...,
        description="UUID identifier for this query (for tracking/debugging)"
    )
    total_results: int = Field(
        ...,
        description="Total number of results returned",
        ge=0
    )
