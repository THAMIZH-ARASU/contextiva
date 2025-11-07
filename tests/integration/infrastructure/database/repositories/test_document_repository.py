"""Integration tests for DocumentRepository."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.models.document import Document, DocumentType
from src.infrastructure.database.repositories.document_repository import (
    DocumentRepository,
)
from src.shared.utils.errors import DocumentNotFoundError


@pytest.fixture
async def cleanup_documents(db_pool):
    """Clean up documents table after each test."""
    yield
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM knowledge_items")
        await conn.execute("DELETE FROM documents")


@pytest.mark.asyncio
class TestDocumentRepository:
    """Integration tests for DocumentRepository."""

    async def test_create_document(self, db_pool, cleanup_documents, test_project_id):
        """Test creating a document in the database."""
        # Arrange
        repo = DocumentRepository(db_pool)
        doc = Document(
            id=uuid4(),
            project_id=test_project_id,
            name="README.md",
            type=DocumentType.MARKDOWN,
            version="v1.0.0",
            content_hash="a" * 64,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Act
        created = await repo.create(doc)

        # Assert
        assert created.id == doc.id
        assert created.project_id == test_project_id
        assert created.name == "README.md"
        assert created.type == DocumentType.MARKDOWN
        assert created.version == "v1.0.0"

    async def test_get_by_id_existing(self, db_pool, cleanup_documents, test_project_id):
        """Test retrieving an existing document by ID."""
        # Arrange
        repo = DocumentRepository(db_pool)
        doc = Document(
            id=uuid4(),
            project_id=test_project_id,
            name="test.pdf",
            type=DocumentType.PDF,
            version="1.0.0",
            content_hash="b" * 64,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await repo.create(doc)

        # Act
        found = await repo.get_by_id(doc.id)

        # Assert
        assert found is not None
        assert found.id == doc.id
        assert found.name == "test.pdf"

    async def test_get_by_id_nonexistent(self, db_pool, cleanup_documents):
        """Test retrieving a non-existent document returns None."""
        # Arrange
        repo = DocumentRepository(db_pool)

        # Act
        found = await repo.get_by_id(uuid4())

        # Assert
        assert found is None

    async def test_get_by_project(self, db_pool, cleanup_documents, test_project_id):
        """Test retrieving all documents for a project."""
        # Arrange
        repo = DocumentRepository(db_pool)
        doc1 = Document(
            id=uuid4(),
            project_id=test_project_id,
            name="doc1.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="c" * 64,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        doc2 = Document(
            id=uuid4(),
            project_id=test_project_id,
            name="doc2.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="d" * 64,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await repo.create(doc1)
        await repo.create(doc2)

        # Act
        docs = await repo.get_by_project(test_project_id)

        # Assert
        assert len(docs) == 2
        doc_ids = [d.id for d in docs]
        assert doc1.id in doc_ids
        assert doc2.id in doc_ids

    async def test_get_all_versions(self, db_pool, cleanup_documents, test_project_id):
        """Test retrieving all versions of a document."""
        # Arrange
        repo = DocumentRepository(db_pool)
        doc_v1 = Document(
            id=uuid4(),
            project_id=test_project_id,
            name="spec.md",
            type=DocumentType.MARKDOWN,
            version="v1.0.0",
            content_hash="e" * 64,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        doc_v2 = Document(
            id=uuid4(),
            project_id=test_project_id,
            name="spec.md",
            type=DocumentType.MARKDOWN,
            version="v2.0.0",
            content_hash="f" * 64,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await repo.create(doc_v1)
        await repo.create(doc_v2)

        # Act
        versions = await repo.get_all_versions(test_project_id, "spec.md")

        # Assert
        assert len(versions) == 2
        # Should be ordered by version DESC
        assert versions[0].version == "v2.0.0"
        assert versions[1].version == "v1.0.0"

    async def test_update_document(self, db_pool, cleanup_documents, test_project_id):
        """Test updating an existing document."""
        # Arrange
        repo = DocumentRepository(db_pool)
        doc = Document(
            id=uuid4(),
            project_id=test_project_id,
            name="old.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="g" * 64,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        created = await repo.create(doc)

        # Act
        created.name = "new.md"
        created.version = "2.0.0"
        updated = await repo.update(created)

        # Assert
        assert updated.name == "new.md"
        assert updated.version == "2.0.0"

    async def test_update_nonexistent_raises_error(self, db_pool, cleanup_documents):
        """Test updating non-existent document raises error."""
        # Arrange
        repo = DocumentRepository(db_pool)
        doc = Document(
            id=uuid4(),
            project_id=uuid4(),
            name="ghost.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="h" * 64,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Act & Assert
        with pytest.raises(DocumentNotFoundError):
            await repo.update(doc)

    async def test_delete_document(self, db_pool, cleanup_documents, test_project_id):
        """Test deleting a document."""
        # Arrange
        repo = DocumentRepository(db_pool)
        doc = Document(
            id=uuid4(),
            project_id=test_project_id,
            name="delete_me.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="i" * 64,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await repo.create(doc)

        # Act
        deleted = await repo.delete(doc.id)

        # Assert
        assert deleted is True
        found = await repo.get_by_id(doc.id)
        assert found is None

    async def test_delete_nonexistent_returns_false(self, db_pool, cleanup_documents):
        """Test deleting non-existent document returns False."""
        # Arrange
        repo = DocumentRepository(db_pool)

        # Act
        deleted = await repo.delete(uuid4())

        # Assert
        assert deleted is False

    async def test_cascade_delete_with_knowledge_items(
        self, db_pool, cleanup_documents, test_project_id
    ):
        """Test that deleting a document cascades to knowledge items."""
        # Arrange
        repo = DocumentRepository(db_pool)
        doc = Document(
            id=uuid4(),
            project_id=test_project_id,
            name="cascade.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="j" * 64,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await repo.create(doc)

        # Create a knowledge item linked to this document
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO knowledge_items (id, document_id, chunk_text, chunk_index, embedding, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5::vector, $6::jsonb, $7)
                """,
                uuid4(),
                doc.id,
                "Test chunk",
                0,
                [0.1] * 1536,
                {},
                datetime.utcnow(),
            )

        # Act
        await repo.delete(doc.id)

        # Assert - knowledge items should be deleted via CASCADE
        async with db_pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM knowledge_items WHERE document_id = $1",
                doc.id,
            )
            assert count == 0
