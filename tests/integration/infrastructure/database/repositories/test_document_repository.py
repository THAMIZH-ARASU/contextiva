"""Integration tests for DocumentRepository."""

import pytest
import asyncpg
from datetime import datetime
from uuid import uuid4

from src.domain.models.document import Document, DocumentType
from src.infrastructure.database.repositories.document_repository import DocumentRepository
from src.shared.config.settings import load_settings
from src.shared.utils.errors import DocumentNotFoundError


async def get_fresh_pool():
    """Create a fresh connection pool for each test (bypass singleton)."""
    settings = load_settings()
    return await asyncpg.create_pool(dsn=settings.db.dsn, min_size=1, max_size=5)


async def create_test_project():
    """Helper to create a test project and return pool + project_id."""
    pool = await get_fresh_pool()
    project_id = uuid4()
    owner_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO projects (id, name, description, status, tags, owner_id, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            """,
            project_id,
            "Test Project",
            "Integration test project",
            "Active",
            [],
            owner_id,
        )
    return pool, project_id


async def cleanup_test_project(pool, project_id):
    """Cleanup test project (CASCADE delete) and close pool."""
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM projects WHERE id = $1", project_id)
    await pool.close()


@pytest.mark.asyncio
class TestDocumentRepository:
    """Integration tests for DocumentRepository using real PostgreSQL database."""

    async def test_create_document(self):
        """Test creating a new document."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = DocumentRepository(pool)
        doc_id = uuid4()
        now = datetime.utcnow()
        doc = Document(
            id=doc_id,
            project_id=project_id,
            name="test.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="a" * 64,  # Valid SHA-256
            created_at=now,
            updated_at=now,
        )

        try:
            # Act
            created = await repo.create(doc)

            # Assert
            assert created.id == doc_id
            assert created.project_id == project_id
            assert created.name == "test.md"
            assert created.type == DocumentType.MARKDOWN
            assert created.version == "1.0.0"
            assert created.content_hash == "a" * 64
            assert isinstance(created.created_at, datetime)
            assert isinstance(created.updated_at, datetime)
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_get_by_id_existing(self):
        """Test retrieving an existing document by ID."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = DocumentRepository(pool)
        doc_id = uuid4()
        now = datetime.utcnow()
        doc = Document(
            id=doc_id,
            project_id=project_id,
            name="test.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="b" * 64,
            created_at=now,
            updated_at=now,
        )
        await repo.create(doc)

        try:
            # Act
            retrieved = await repo.get_by_id(doc_id)

            # Assert
            assert retrieved is not None
            assert retrieved.id == doc_id
            assert retrieved.name == "test.md"
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_get_by_id_nonexistent(self):
        """Test retrieving a non-existent document returns None."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = DocumentRepository(pool)
        nonexistent_id = uuid4()

        try:
            # Act
            result = await repo.get_by_id(nonexistent_id)

            # Assert
            assert result is None
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_get_by_project(self):
        """Test retrieving all documents for a project."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = DocumentRepository(pool)
        now = datetime.utcnow()
        doc1 = Document(
            id=uuid4(),
            project_id=project_id,
            name="doc1.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="c" * 64,
            created_at=now,
            updated_at=now,
        )
        doc2 = Document(
            id=uuid4(),
            project_id=project_id,
            name="doc2.pdf",
            type=DocumentType.PDF,
            version="1.0.0",
            content_hash="d" * 64,
            created_at=now,
            updated_at=now,
        )
        await repo.create(doc1)
        await repo.create(doc2)

        try:
            # Act
            documents = await repo.get_by_project(project_id)

            # Assert
            assert len(documents) == 2
            names = {doc.name for doc in documents}
            assert names == {"doc1.md", "doc2.pdf"}
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_get_all_versions(self):
        """Test retrieving all versions of a document."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = DocumentRepository(pool)
        doc_name = "versioned.md"
        now = datetime.utcnow()
        
        # Create multiple versions
        doc_v1 = Document(
            id=uuid4(),
            project_id=project_id,
            name=doc_name,
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="e" * 64,
            created_at=now,
            updated_at=now,
        )
        doc_v2 = Document(
            id=uuid4(),
            project_id=project_id,
            name=doc_name,
            type=DocumentType.MARKDOWN,
            version="2.0.0",
            content_hash="f" * 64,
            created_at=now,
            updated_at=now,
        )
        doc_v3 = Document(
            id=uuid4(),
            project_id=project_id,
            name=doc_name,
            type=DocumentType.MARKDOWN,
            version="3.0.0",
            content_hash="1" * 64,
            created_at=now,
            updated_at=now,
        )
        await repo.create(doc_v1)
        await repo.create(doc_v2)
        await repo.create(doc_v3)

        try:
            # Act
            versions = await repo.get_all_versions(project_id, doc_name)

            # Assert
            assert len(versions) == 3
            # Should be ordered DESC by version
            assert versions[0].version == "3.0.0"
            assert versions[1].version == "2.0.0"
            assert versions[2].version == "1.0.0"
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_update_document(self):
        """Test updating a document."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = DocumentRepository(pool)
        doc_id = uuid4()
        now = datetime.utcnow()
        doc = Document(
            id=doc_id,
            project_id=project_id,
            name="original.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="2" * 64,
            created_at=now,
            updated_at=now,
        )
        await repo.create(doc)

        try:
            # Act - Update version
            updated_doc = Document(
                id=doc_id,
                project_id=project_id,
                name="original.md",
                type=DocumentType.MARKDOWN,
                version="2.0.0",
                content_hash="3" * 64,
                created_at=now,
                updated_at=now,
            )
            result = await repo.update(updated_doc)

            # Assert
            assert result.version == "2.0.0"
            assert result.content_hash == "3" * 64
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_update_nonexistent_raises_error(self):
        """Test updating non-existent document raises error."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = DocumentRepository(pool)
        now = datetime.utcnow()
        nonexistent_doc = Document(
            id=uuid4(),
            project_id=project_id,
            name="nonexistent.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="4" * 64,
            created_at=now,
            updated_at=now,
        )

        try:
            # Act & Assert
            with pytest.raises(DocumentNotFoundError):
                await repo.update(nonexistent_doc)
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_delete_document(self):
        """Test deleting a document."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = DocumentRepository(pool)
        doc_id = uuid4()
        now = datetime.utcnow()
        doc = Document(
            id=doc_id,
            project_id=project_id,
            name="to_delete.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="5" * 64,
            created_at=now,
            updated_at=now,
        )
        await repo.create(doc)

        try:
            # Act
            result = await repo.delete(doc_id)

            # Assert
            assert result is True
            deleted = await repo.get_by_id(doc_id)
            assert deleted is None
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_delete_nonexistent_returns_false(self):
        """Test deleting non-existent document returns False."""
        # Arrange
        pool, project_id = await create_test_project()
        repo = DocumentRepository(pool)
        nonexistent_id = uuid4()

        try:
            # Act
            result = await repo.delete(nonexistent_id)

            # Assert
            assert result is False
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_cascade_delete_with_knowledge_items(self):
        """Test that deleting a document cascades to knowledge_items."""
        # Arrange
        pool, project_id = await create_test_project()
        doc_repo = DocumentRepository(pool)
        doc_id = uuid4()
        now = datetime.utcnow()
        doc = Document(
            id=doc_id,
            project_id=project_id,
            name="with_knowledge.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="6" * 64,
            created_at=now,
            updated_at=now,
        )
        await doc_repo.create(doc)

        # Create a knowledge item linked to the document
        async with pool.acquire() as conn:
            embedding = [0.1] * 1536
            embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
            await conn.execute(
                """
                INSERT INTO knowledge_items (id, document_id, chunk_text, chunk_index, embedding, created_at)
                VALUES ($1, $2, $3, $4, $5::vector, NOW())
                """,
                uuid4(),
                doc_id,
                "Test chunk",
                0,
                embedding_str,  # Convert to string for pgvector
            )

        try:
            # Act - Delete document
            await doc_repo.delete(doc_id)

            # Assert - Knowledge item should be CASCADE deleted
            async with pool.acquire() as conn:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM knowledge_items WHERE document_id = $1", doc_id
                )
            assert count == 0
        finally:
            await cleanup_test_project(pool, project_id)
