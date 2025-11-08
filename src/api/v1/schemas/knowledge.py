"""Knowledge upload request/response schemas."""
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class KnowledgeUploadResponse(BaseModel):
    """Response schema for knowledge upload endpoint."""

    document_id: UUID
    status: str
    message: str


class KnowledgeItemResponse(BaseModel):
    """Response schema for knowledge item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_text: str
    metadata: dict[str, Any]
