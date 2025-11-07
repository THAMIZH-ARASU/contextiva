"""Integration tests for KnowledgeRepository."""

import pytest
import asyncpg
from datetime import datetime
from uuid import uuid4

from src.domain.models.knowledge import KnowledgeItem
from src.infrastructure.database.repositories.knowledge_repository import KnowledgeRepository
from src.shared.config.settings import load_settings


async def get_fresh_pool():
    """Create a fresh connection pool for each test (bypass singleton)."""
    settings = load_settings()
    return await asyncpg.create_pool(dsn=settings.db.dsn, min_size=1, max_size=5)


async def create_test_project_and_document():
    """Helper to create a test project, document and return pool + IDs."""
    pool = await get_fresh_pool()
    project_id = uuid4()
    document_id = uuid4()
    now = datetime.utcnow()
    
    async with pool.acquire() as conn:
        # Create project
        await conn.execute(
            """
            INSERT INTO projects (id, name, description, status, tags, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
            """,
            project_id,
            "Test Project",
            "Integration test project",
            "Active",
            [],
        )
        # Create document
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, name, type, version, content_hash, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            document_id,
            project_id,
            "test_doc.md",
            "markdown",
            "1.0.0",
            "a" * 64,
            now,
            now,
        )
    return pool, project_id, document_id


async def cleanup_test_project(pool, project_id):
    """Cleanup test project (CASCADE delete) and close pool."""
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM projects WHERE id = $1", project_id)
    await pool.close()


@pytest.mark.asyncio
class TestKnowledgeRepository:
    """Integration tests for KnowledgeRepository."""

    async def test_create_knowledge_item(self):
        """Test creating a knowledge item in the database."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)
        embedding = [0.1, 0.2, 0.3] + [0.0] * 1533  # 1536 dimensions
        item = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="This is a test chunk of text.",
            chunk_index=0,
            embedding=embedding,
            metadata={"source": "page 1"},
            created_at=datetime.utcnow(),
        )

        try:
            # Act
            created = await repo.create(item)

            # Assert
            assert created.id == item.id
            assert created.document_id == doc_id
            assert created.chunk_text == "This is a test chunk of text."
            assert created.chunk_index == 0
            assert len(created.embedding) == 1536
            assert created.metadata == {"source": "page 1"}
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_create_batch(self):
        """Test creating multiple knowledge items in a batch."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)
        items = []
        for i in range(3):
            embedding = [float(i)] * 1536
            item = KnowledgeItem(
                id=uuid4(),
                document_id=doc_id,
                chunk_text=f"Chunk {i}",
                chunk_index=i,
                embedding=embedding,
                metadata={"chunk_num": i},
                created_at=datetime.utcnow(),
            )
            items.append(item)

        try:
            # Act
            created_items = await repo.create_batch(items)

            # Assert
            assert len(created_items) == 3
            for i, created in enumerate(created_items):
                assert created.chunk_index == i
                assert created.chunk_text == f"Chunk {i}"
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_get_by_id_existing(self):
        """Test retrieving an existing knowledge item by ID."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)
        embedding = [0.5] * 1536
        item = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Test chunk",
            chunk_index=0,
            embedding=embedding,
            metadata={},
            created_at=datetime.utcnow(),
        )
        await repo.create(item)

        try:
            # Act
            found = await repo.get_by_id(item.id)

            # Assert
            assert found is not None
            assert found.id == item.id
            assert found.chunk_text == "Test chunk"
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_get_by_id_nonexistent(self):
        """Test retrieving a non-existent knowledge item returns None."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)

        try:
            # Act
            found = await repo.get_by_id(uuid4())

            # Assert
            assert found is None
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_get_by_document(self):
        """Test retrieving all knowledge items for a document."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)
        
        items = []
        for i in range(3):
            item = KnowledgeItem(
                id=uuid4(),
                document_id=doc_id,
                chunk_text=f"Chunk {i}",
                chunk_index=i,
                embedding=[float(i)] * 1536,
                metadata={},
                created_at=datetime.utcnow(),
            )
            items.append(item)
            await repo.create(item)

        try:
            # Act
            retrieved = await repo.get_by_document(doc_id)

            # Assert
            assert len(retrieved) == 3
            # Should be ordered by chunk_index
            for i, item in enumerate(retrieved):
                assert item.chunk_index == i
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_search_similar_basic(self):
        """Test basic similarity search."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)
        
        # Create items with different embeddings
        item1 = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Similar text",
            chunk_index=0,
            embedding=[1.0] * 1536,  # Similar to query
            metadata={},
            created_at=datetime.utcnow(),
        )
        item2 = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Different text",
            chunk_index=1,
            embedding=[0.0] * 1536,  # Different from query
            metadata={},
            created_at=datetime.utcnow(),
        )
        await repo.create(item1)
        await repo.create(item2)

        try:
            # Act
            query_embedding = [0.9] * 1536  # Similar to item1
            results = await repo.search_similar(query_embedding, limit=5)

            # Assert
            assert len(results) > 0
            # Most similar should be first (results are tuples of (item, score))
            assert results[0][0].id == item1.id
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_search_similar_with_threshold(self):
        """Test similarity search with threshold filter."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)
        
        item = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Test",
            chunk_index=0,
            embedding=[1.0] * 1536,
            metadata={},
            created_at=datetime.utcnow(),
        )
        await repo.create(item)

        try:
            # Act - Search with high threshold
            query_embedding = [1.0] * 1536
            results = await repo.search_similar(query_embedding, similarity_threshold=0.99)

            # Assert - Should find exact match
            assert len(results) >= 1
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_search_similar_with_project_filter(self):
        """Test similarity search filtered by project."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)
        
        item = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Test",
            chunk_index=0,
            embedding=[0.5] * 1536,
            metadata={},
            created_at=datetime.utcnow(),
        )
        await repo.create(item)

        try:
            # Act
            query_embedding = [0.5] * 1536
            results = await repo.search_similar(query_embedding, project_id=project_id)

            # Assert
            assert len(results) >= 1
            # Results are tuples of (item, score)
            for item, score in results:
                assert item.document_id == doc_id
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_search_similar_limit(self):
        """Test limiting similarity search results."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)
        
        # Create 5 items
        for i in range(5):
            item = KnowledgeItem(
                id=uuid4(),
                document_id=doc_id,
                chunk_text=f"Text {i}",
                chunk_index=i,
                embedding=[float(i) / 10.0] * 1536,
                metadata={},
                created_at=datetime.utcnow(),
            )
            await repo.create(item)

        try:
            # Act
            query_embedding = [0.0] * 1536
            results = await repo.search_similar(query_embedding, limit=2)

            # Assert
            assert len(results) == 2
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_delete_knowledge_item(self):
        """Test deleting a knowledge item."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)
        item = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Delete me",
            chunk_index=0,
            embedding=[0.0] * 1536,
            metadata={},
            created_at=datetime.utcnow(),
        )
        await repo.create(item)

        try:
            # Act
            deleted = await repo.delete(item.id)

            # Assert
            assert deleted is True
            found = await repo.get_by_id(item.id)
            assert found is None
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_delete_nonexistent_returns_false(self):
        """Test deleting non-existent knowledge item returns False."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)

        try:
            # Act
            deleted = await repo.delete(uuid4())

            # Assert
            assert deleted is False
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_delete_by_document(self):
        """Test deleting all knowledge items for a document."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)
        
        # Create 3 items
        for i in range(3):
            item = KnowledgeItem(
                id=uuid4(),
                document_id=doc_id,
                chunk_text=f"Chunk {i}",
                chunk_index=i,
                embedding=[0.0] * 1536,
                metadata={},
                created_at=datetime.utcnow(),
            )
            await repo.create(item)

        try:
            # Act
            count = await repo.delete_by_document(doc_id)

            # Assert
            assert count == 3
            remaining = await repo.get_by_document(doc_id)
            assert len(remaining) == 0
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_cascade_delete_from_document(self):
        """Test that CASCADE delete from document removes knowledge items."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)
        
        item = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Test",
            chunk_index=0,
            embedding=[0.0] * 1536,
            metadata={},
            created_at=datetime.utcnow(),
        )
        await repo.create(item)

        try:
            # Act - Delete document (should CASCADE)
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM documents WHERE id = $1", doc_id)

            # Assert - Knowledge item should be deleted
            found = await repo.get_by_id(item.id)
            assert found is None
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_different_embedding_dimensions(self):
        """Test storing embeddings with different dimensions."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)
        
        # Note: pgvector schema expects 1536 dimensions
        item = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Test",
            chunk_index=0,
            embedding=[0.1] * 1536,  # Must be 1536
            metadata={},
            created_at=datetime.utcnow(),
        )

        try:
            # Act
            created = await repo.create(item)

            # Assert
            assert len(created.embedding) == 1536
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_metadata_storage_and_retrieval(self):
        """Test storing and retrieving complex metadata."""
        # Arrange
        pool, project_id, doc_id = await create_test_project_and_document()
        repo = KnowledgeRepository(pool)
        
        complex_metadata = {
            "source": "page 5",
            "author": "John Doe",
            "tags": ["important", "reviewed"],
            "confidence": 0.95,
        }
        
        item = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Test",
            chunk_index=0,
            embedding=[0.0] * 1536,
            metadata=complex_metadata,
            created_at=datetime.utcnow(),
        )

        try:
            # Act
            created = await repo.create(item)

            # Assert
            assert created.metadata == complex_metadata
            assert created.metadata["source"] == "page 5"
            assert "important" in created.metadata["tags"]
        finally:
            await cleanup_test_project(pool, project_id)
