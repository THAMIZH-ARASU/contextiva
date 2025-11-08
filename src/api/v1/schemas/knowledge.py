"""Knowledge upload request/response schemas."""
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class KnowledgeUploadResponse(BaseModel):
    """Response schema for knowledge upload endpoint."""

    document_id: UUID
    status: str
    message: str


class KnowledgeItemResponse(BaseModel):
    """Response schema for knowledge item."""

    id: UUID
    document_id: UUID
    chunk_text: str
    metadata: dict[str, Any]

    class Config:
        """Pydantic configuration."""

        from_attributes = True
