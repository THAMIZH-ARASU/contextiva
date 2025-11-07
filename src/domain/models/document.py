"""Document domain model and repository interface.

This module defines the Document entity and its repository interface
for managing document lifecycle, versioning, and storage.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class DocumentType(str, Enum):
    """Supported document types for ingestion."""

    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    TEXT = "text"


@dataclass(slots=True)
class Document:
    """Document entity representing an ingested document with versioning.
    
    Attributes:
        id: Unique identifier for the document
        project_id: Foreign key to the parent project
        name: Human-readable document name
        type: Document type (markdown, pdf, docx, html, text)
        version: Semantic version (e.g., v1.0.0, 1.2.3)
        content_hash: SHA-256 hash of content for deduplication
        created_at: Timestamp when document was created
        updated_at: Timestamp when document was last updated
    """

    id: UUID
    project_id: UUID
    name: str
    type: DocumentType
    version: str
    content_hash: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Validate document attributes after initialization."""
        # Validate name is not empty
        if not self.name or not self.name.strip():
            raise ValueError("Document name cannot be empty")

        # Validate semantic versioning format
        version_pattern = r"^v?\d+\.\d+\.\d+$"
        if not re.match(version_pattern, self.version):
            raise ValueError(
                f"Invalid version format: {self.version}. "
                "Must follow semantic versioning (e.g., v1.0.0 or 1.2.3)"
            )

        # Validate content hash is SHA-256 (64 hex chars)
        if not re.match(r"^[a-fA-F0-9]{64}$", self.content_hash):
            raise ValueError(
                f"Invalid content_hash: {self.content_hash}. "
                "Must be a valid SHA-256 hash (64 hexadecimal characters)"
            )

        # Ensure type is a DocumentType enum
        if isinstance(self.type, str):
            self.type = DocumentType(self.type)


class IDocumentRepository(ABC):
    """Repository interface for Document entity operations."""

    @abstractmethod
    async def create(self, document: Document) -> Document:
        """Create a new document.
        
        Args:
            document: Document entity to create
            
        Returns:
            Created document with generated fields populated
            
        Raises:
            ValueError: If document validation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> Optional[Document]:
        """Retrieve a document by its ID.
        
        Args:
            document_id: Unique identifier of the document
            
        Returns:
            Document if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_project(
        self, project_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        """Retrieve all documents for a project.
        
        Args:
            project_id: ID of the project
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of documents belonging to the project
        """
        pass

    @abstractmethod
    async def get_all_versions(self, project_id: UUID, name: str) -> list[Document]:
        """Retrieve all versions of a document by name.
        
        Args:
            project_id: ID of the project
            name: Name of the document
            
        Returns:
            List of all versions of the document, ordered by version
        """
        pass

    @abstractmethod
    async def update(self, document: Document) -> Document:
        """Update an existing document.
        
        Args:
            document: Document entity with updated values
            
        Returns:
            Updated document
            
        Raises:
            DocumentNotFoundError: If document doesn't exist
        """
        pass

    @abstractmethod
    async def delete(self, document_id: UUID) -> bool:
        """Delete a document by ID.
        
        Args:
            document_id: Unique identifier of the document
            
        Returns:
            True if deleted, False if not found
        """
        pass
