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
        use_hybrid_search: Optional flag to enable hybrid vector + keyword search.
        use_re_ranking: Optional flag to enable LLM-based re-ranking of results.
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
    use_hybrid_search: bool = Field(
        False,
        description="Enable hybrid search combining vector and keyword (BM25) search"
    )
    use_re_ranking: bool = Field(
        False,
        description="Enable LLM-based re-ranking of search results"
    )
    use_agentic_rag: bool = Field(
        False,
        description="Enable agentic RAG to generate a synthesized natural language answer"
    )


class KnowledgeItemResult(BaseModel):
    """Individual knowledge item result from RAG query.
    
    Attributes:
        id: UUID of the knowledge item.
        chunk_text: The text content of the chunk.
        similarity_score: Cosine similarity score (0-1, higher is more similar).
        bm25_score: Optional BM25/keyword search score (if hybrid search used).
        rerank_score: Optional re-ranking score from LLM (if re-ranking used).
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
    bm25_score: Optional[float] = Field(
        None,
        description="BM25/keyword search score (if hybrid search used)"
    )
    rerank_score: Optional[float] = Field(
        None,
        description="Re-ranking score from LLM (if re-ranking used)"
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
    synthesized_answer: Optional[str] = Field(
        None,
        description="Optional synthesized natural language answer (when use_agentic_rag=true)"
    )
