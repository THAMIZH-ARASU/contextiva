"""Integration tests for KnowledgeRepository vector_search method."""

import pytest
import asyncpg
from datetime import datetime
from uuid import uuid4

from src.domain.models.document import Document, DocumentType
from src.domain.models.knowledge import KnowledgeItem
from src.infrastructure.database.repositories.knowledge_repository import KnowledgeRepository
from src.infrastructure.database.repositories.document_repository import DocumentRepository
from src.shared.config.settings import load_settings


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
class TestKnowledgeRepositoryVectorSearch:
    """Integration tests for KnowledgeRepository vector_search using real PostgreSQL database."""

    async def test_vector_search_returns_correct_results(self):
        """Test vector_search returns correct results ordered by similarity."""
        # Arrange
        pool, project_id = await create_test_project()
        doc_repo = DocumentRepository(pool)
        knowledge_repo = KnowledgeRepository(pool)
        
        now = datetime.utcnow()
        
        # Create document
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            project_id=project_id,
            name="test.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="a" * 64,
            created_at=now,
            updated_at=now,
        )
        await doc_repo.create(doc)
        
        # Create knowledge items with different embeddings
        # Use embeddings that differ in direction for proper cosine similarity testing
        query_embedding = [1.0] + [0.0] * 1535  # Vector pointing in first dimension
        similar_embedding = [0.9] + [0.1] * 1535  # Similar direction
        dissimilar_embedding = [0.1] + [0.9] * 1535  # Different direction
        
        item1_id = uuid4()
        item1 = KnowledgeItem(
            id=item1_id,
            document_id=doc_id,
            chunk_text="Similar chunk",
            chunk_index=0,
            embedding=similar_embedding,
            metadata={},
            created_at=now,
        )
        
        item2_id = uuid4()
        item2 = KnowledgeItem(
            id=item2_id,
            document_id=doc_id,
            chunk_text="Dissimilar chunk",
            chunk_index=1,
            embedding=dissimilar_embedding,
            metadata={},
            created_at=now,
        )
        
        await knowledge_repo.create(item1)
        await knowledge_repo.create(item2)
        
        try:
            # Act
            results = await knowledge_repo.vector_search(
                project_id=project_id,
                query_embedding=query_embedding,
                top_k=10,
            )
            
            # Assert
            assert len(results) == 2
            # First result should be more similar
            assert results[0][0].id == item1_id
            assert results[0][1] > results[1][1]  # Higher similarity score
            assert results[1][0].id == item2_id
            # Similarity scores should be between 0 and 1
            assert 0.0 <= results[0][1] <= 1.0
            assert 0.0 <= results[1][1] <= 1.0
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_vector_search_filters_by_project_id(self):
        """Test vector_search filters by project_id (only returns items from specified project)."""
        # Arrange
        pool1, project_id1 = await create_test_project()
        pool2, project_id2 = await create_test_project()
        
        doc_repo1 = DocumentRepository(pool1)
        doc_repo2 = DocumentRepository(pool2)
        knowledge_repo1 = KnowledgeRepository(pool1)
        knowledge_repo2 = KnowledgeRepository(pool2)
        
        now = datetime.utcnow()
        
        # Create document for project 1
        doc1_id = uuid4()
        doc1 = Document(
            id=doc1_id,
            project_id=project_id1,
            name="doc1.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="a" * 64,
            created_at=now,
            updated_at=now,
        )
        await doc_repo1.create(doc1)
        
        # Create document for project 2
        doc2_id = uuid4()
        doc2 = Document(
            id=doc2_id,
            project_id=project_id2,
            name="doc2.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="b" * 64,
            created_at=now,
            updated_at=now,
        )
        await doc_repo2.create(doc2)
        
        # Create knowledge items for both projects with same embedding
        embedding = [0.5] * 1536
        
        item1_id = uuid4()
        item1 = KnowledgeItem(
            id=item1_id,
            document_id=doc1_id,
            chunk_text="Project 1 chunk",
            chunk_index=0,
            embedding=embedding,
            metadata={},
            created_at=now,
        )
        await knowledge_repo1.create(item1)
        
        item2_id = uuid4()
        item2 = KnowledgeItem(
            id=item2_id,
            document_id=doc2_id,
            chunk_text="Project 2 chunk",
            chunk_index=0,
            embedding=embedding,
            metadata={},
            created_at=now,
        )
        await knowledge_repo2.create(item2)
        
        try:
            # Act: Search only project1
            results = await knowledge_repo1.vector_search(
                project_id=project_id1,
                query_embedding=embedding,
                top_k=10,
            )
            
            # Assert: Only project1 item returned
            assert len(results) == 1
            assert results[0][0].id == item1_id
        finally:
            await cleanup_test_project(pool1, project_id1)
            await cleanup_test_project(pool2, project_id2)

    async def test_vector_search_top_k_limit(self):
        """Test vector_search enforces top_k limit."""
        # Arrange
        pool, project_id = await create_test_project()
        doc_repo = DocumentRepository(pool)
        knowledge_repo = KnowledgeRepository(pool)
        
        now = datetime.utcnow()
        
        # Create document
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            project_id=project_id,
            name="test.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="a" * 64,
            created_at=now,
            updated_at=now,
        )
        await doc_repo.create(doc)
        
        # Create 10 knowledge items with same embedding
        embedding = [0.5] * 1536
        for i in range(10):
            item = KnowledgeItem(
                id=uuid4(),
                document_id=doc_id,
                chunk_text=f"Chunk {i}",
                chunk_index=i,
                embedding=embedding,
                metadata={},
                created_at=now,
            )
            await knowledge_repo.create(item)
        
        try:
            # Act: Request only top 3
            results = await knowledge_repo.vector_search(
                project_id=project_id,
                query_embedding=embedding,
                top_k=3,
            )
            
            # Assert: Only 3 returned
            assert len(results) == 3
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_vector_search_empty_results(self):
        """Test vector_search returns empty list for project with no documents."""
        # Arrange
        pool, project_id = await create_test_project()
        knowledge_repo = KnowledgeRepository(pool)
        
        try:
            # Act
            results = await knowledge_repo.vector_search(
                project_id=project_id,
                query_embedding=[0.5] * 1536,
                top_k=10,
            )
            
            # Assert
            assert len(results) == 0
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_vector_search_similarity_scores_ordered(self):
        """Test vector_search returns results ordered by similarity score (descending)."""
        # Arrange
        pool, project_id = await create_test_project()
        doc_repo = DocumentRepository(pool)
        knowledge_repo = KnowledgeRepository(pool)
        
        now = datetime.utcnow()
        
        # Create document
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            project_id=project_id,
            name="test.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="a" * 64,
            created_at=now,
            updated_at=now,
        )
        await doc_repo.create(doc)
        
        # Create items with varying similarity to query
        query_embedding = [0.5] * 1536
        embeddings = [
            [0.51] * 1536,  # Very similar
            [0.45] * 1536,  # Moderately similar
            [0.1] * 1536,   # Less similar
        ]
        
        for i, emb in enumerate(embeddings):
            item = KnowledgeItem(
                id=uuid4(),
                document_id=doc_id,
                chunk_text=f"Chunk {i}",
                chunk_index=i,
                embedding=emb,
                metadata={},
                created_at=now,
            )
            await knowledge_repo.create(item)
        
        try:
            # Act
            results = await knowledge_repo.vector_search(
                project_id=project_id,
                query_embedding=query_embedding,
                top_k=10,
            )
            
            # Assert: Scores should be in descending order
            assert len(results) == 3
            scores = [score for _, score in results]
            assert scores == sorted(scores, reverse=True)
            # All scores should be between 0 and 1
            for score in scores:
                assert 0.0 <= score <= 1.0
        finally:
            await cleanup_test_project(pool, project_id)
