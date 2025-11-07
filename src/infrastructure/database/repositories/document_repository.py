"""PostgreSQL implementation of IDocumentRepository.

This module provides the concrete repository implementation for Document entities
using asyncpg and PostgreSQL.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from asyncpg import Pool

from src.domain.models.document import Document, DocumentType, IDocumentRepository
from src.shared.utils.errors import DocumentNotFoundError


class DocumentRepository(IDocumentRepository):
    """PostgreSQL implementation of document repository."""

    def __init__(self, pool: Pool) -> None:
        """Initialize repository with database connection pool.
        
        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def create(self, document: Document) -> Document:
        """Create a new document in the database.
        
        Args:
            document: Document entity to create
            
        Returns:
            Created document with timestamps populated
        """
        query = """
            INSERT INTO documents (
                id, project_id, name, type, version, content_hash, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, project_id, name, type, version, content_hash, created_at, updated_at
        """
        now = datetime.utcnow()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                document.id,
                document.project_id,
                document.name,
                document.type.value,
                document.version,
                document.content_hash,
                now,
                now,
            )

        if not row:
            raise RuntimeError("Failed to create document - no row returned")

        return Document(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            type=DocumentType(row["type"]),
            version=row["version"],
            content_hash=row["content_hash"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_by_id(self, document_id: UUID) -> Optional[Document]:
        """Retrieve a document by ID.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Document if found, None otherwise
        """
        query = """
            SELECT id, project_id, name, type, version, content_hash, created_at, updated_at
            FROM documents
            WHERE id = $1
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, document_id)

        if not row:
            return None

        return Document(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            type=DocumentType(row["type"]),
            version=row["version"],
            content_hash=row["content_hash"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_by_project(
        self, project_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        """Retrieve all documents for a project.
        
        Args:
            project_id: Project identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of documents for the project
        """
        query = """
            SELECT id, project_id, name, type, version, content_hash, created_at, updated_at
            FROM documents
            WHERE project_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, project_id, limit, skip)

        return [
            Document(
                id=row["id"],
                project_id=row["project_id"],
                name=row["name"],
                type=DocumentType(row["type"]),
                version=row["version"],
                content_hash=row["content_hash"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    async def get_all_versions(self, project_id: UUID, name: str) -> list[Document]:
        """Retrieve all versions of a document.
        
        Args:
            project_id: Project identifier
            name: Document name
            
        Returns:
            List of all versions, ordered by version descending
        """
        query = """
            SELECT id, project_id, name, type, version, content_hash, created_at, updated_at
            FROM documents
            WHERE project_id = $1 AND name = $2
            ORDER BY version DESC
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, project_id, name)

        return [
            Document(
                id=row["id"],
                project_id=row["project_id"],
                name=row["name"],
                type=DocumentType(row["type"]),
                version=row["version"],
                content_hash=row["content_hash"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    async def update(self, document: Document) -> Document:
        """Update an existing document.
        
        Args:
            document: Document with updated values
            
        Returns:
            Updated document
            
        Raises:
            DocumentNotFoundError: If document doesn't exist
        """
        query = """
            UPDATE documents
            SET name = $2, type = $3, version = $4, content_hash = $5, updated_at = $6
            WHERE id = $1
            RETURNING id, project_id, name, type, version, content_hash, created_at, updated_at
        """
        now = datetime.utcnow()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                document.id,
                document.name,
                document.type.value,
                document.version,
                document.content_hash,
                now,
            )

        if not row:
            raise DocumentNotFoundError(f"Document with id {document.id} not found")

        return Document(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            type=DocumentType(row["type"]),
            version=row["version"],
            content_hash=row["content_hash"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def delete(self, document_id: UUID) -> bool:
        """Delete a document by ID.
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if deleted, False if not found
        """
        query = "DELETE FROM documents WHERE id = $1"

        async with self.pool.acquire() as conn:
            result = await conn.execute(query, document_id)

        # Result is like "DELETE 1" or "DELETE 0"
        return result.endswith("1")
