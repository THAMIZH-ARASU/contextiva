"""Pydantic schemas for Document API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.models.document import DocumentType


class DocumentCreate(BaseModel):
    """Schema for creating a new document."""
    
    project_id: UUID = Field(..., description="Project identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Document name")
    type: DocumentType = Field(
        ..., description="Document type (markdown, pdf, docx, html, text)"
    )
    content_hash: str = Field(
        ...,
        pattern=r"^[a-fA-F0-9]{64}$",
        description="SHA-256 content hash (64 hex characters)",
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "project_id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Architecture Documentation",
                    "type": "markdown",
                    "content_hash": "a" * 64
                }
            ]
        }
    }


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata."""
    
    name: str | None = Field(None, min_length=1, max_length=255, description="Document name")
    tags: list[str] | None = Field(None, description="List of document tags")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Updated Architecture Documentation",
                    "tags": ["architecture", "design", "v2"]
                }
            ]
        }
    }


class DocumentVersionCreate(BaseModel):
    """Schema for creating a new document version."""

    content_hash: str = Field(
        ...,
        pattern=r"^[a-fA-F0-9]{64}$",
        description="SHA-256 content hash (64 hex characters)",
    )
    bump_type: Literal["major", "minor", "patch"] = Field(
        ..., description="Version bump type"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content_hash": "b" * 64,
                    "bump_type": "minor"
                }
            ]
        }
    }


class DocumentResponse(BaseModel):
    """Response schema for document data."""
    
    id: UUID
    project_id: UUID
    name: str
    type: DocumentType
    version: str
    content_hash: str
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,  # Pydantic v2 ORM mode
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "project_id": "550e8400-e29b-41d4-a716-446655440001",
                    "name": "Architecture Documentation",
                    "type": "markdown",
                    "version": "v1.0.0",
                    "content_hash": "a" * 64,
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z"
                }
            ]
        }
    }


class DocumentListResponse(BaseModel):
    """Response schema for document list with pagination."""
    
    documents: list[DocumentResponse]
    total: int = Field(..., description="Total number of documents")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Maximum number of records returned")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "documents": [],
                    "total": 0,
                    "skip": 0,
                    "limit": 100
                }
            ]
        }
    }
