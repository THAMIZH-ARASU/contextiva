"""Integration tests for KnowledgeRepository keyword_search method with real PostgreSQL."""

import pytest
import asyncpg
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.models.document import Document, DocumentType
from src.domain.models.knowledge import KnowledgeItem
from src.infrastructure.database.repositories.knowledge_repository import KnowledgeRepository
from src.infrastructure.database.repositories.document_repository import DocumentRepository
from src.shared.config.settings import load_settings


async def get_fresh_pool():
    """Create a fresh connection pool for each test (bypass singleton)."""
    import os
    # Use environment variable if set, otherwise build DSN for local testing
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        # For local testing: connect to Docker container on localhost:5433
        # Note: Docker exposes postgres on 5433, Redis on 6379
        dsn = "postgresql://tumblrs:Saran%402004@localhost:5433/contextiva"
    return await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)


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
class TestKnowledgeRepositoryKeywordSearch:
    """Integration tests for KnowledgeRepository keyword_search using real PostgreSQL database."""

    async def test_keyword_search_returns_results_ordered_by_bm25_score(self):
        """Test keyword_search returns results ordered by BM25 relevance score."""
        # Arrange
        pool, project_id = await create_test_project()
        doc_repo = DocumentRepository(pool)
        knowledge_repo = KnowledgeRepository(pool)
        
        now = datetime.now(timezone.utc)
        
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
        
        # Create knowledge items with different relevance to query "machine learning"
        # Item 1: Contains query multiple times (should rank highest)
        item1_id = uuid4()
        item1 = KnowledgeItem(
            id=item1_id,
            document_id=doc_id,
            chunk_text="Machine learning is a subset of artificial intelligence. Machine learning algorithms learn from data.",
            chunk_index=0,
            embedding=[0.1] * 1536,
            metadata={},
            created_at=now,
        )
        
        # Item 2: Contains query once (should rank second)
        item2_id = uuid4()
        item2 = KnowledgeItem(
            id=item2_id,
            document_id=doc_id,
            chunk_text="Deep learning uses neural networks for machine learning tasks.",
            chunk_index=1,
            embedding=[0.2] * 1536,
            metadata={},
            created_at=now,
        )
        
        # Item 3: Doesn't contain query (should not appear in results)
        item3_id = uuid4()
        item3 = KnowledgeItem(
            id=item3_id,
            document_id=doc_id,
            chunk_text="Data science involves statistics and programming.",
            chunk_index=2,
            embedding=[0.3] * 1536,
            metadata={},
            created_at=now,
        )
        
        await knowledge_repo.create(item1)
        await knowledge_repo.create(item2)
        await knowledge_repo.create(item3)
        
        try:
            # Act
            results = await knowledge_repo.keyword_search(
                project_id=project_id,
                query_text="machine learning",
                top_k=10
            )
            
            # Assert
            assert len(results) == 2, "Should return 2 matching results"
            
            # Check first result (highest BM25 score)
            first_item, first_score = results[0]
            assert first_item.id == item1_id, "Item with most matches should rank first"
            assert first_score > 0, "BM25 score should be positive"
            
            # Check second result
            second_item, second_score = results[1]
            assert second_item.id == item2_id, "Item with fewer matches should rank second"
            assert second_score > 0, "BM25 score should be positive"
            
            # Scores should be ordered descending
            assert first_score >= second_score, "Results should be ordered by BM25 score (descending)"
            
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_keyword_search_filters_by_project_id(self):
        """Test keyword_search only returns results from the specified project."""
        # Arrange
        pool1, project_id1 = await create_test_project()
        pool2, project_id2 = await create_test_project()
        
        doc_repo = DocumentRepository(pool1)
        knowledge_repo = KnowledgeRepository(pool1)
        
        now = datetime.now(timezone.utc)
        
        # Create document in project 1
        doc1_id = uuid4()
        doc1 = Document(
            id=doc1_id,
            project_id=project_id1,
            name="project1.md",
            type=DocumentType.MARKDOWN,
            version="1.0.0",
            content_hash="a" * 64,
            created_at=now,
            updated_at=now,
        )
        await doc_repo.create(doc1)
        
        # Create knowledge item in project 1
        item1_id = uuid4()
        item1 = KnowledgeItem(
            id=item1_id,
            document_id=doc1_id,
            chunk_text="Python programming is widely used in data science and machine learning.",
            chunk_index=0,
            embedding=[0.1] * 1536,
            metadata={},
            created_at=now,
        )
        await knowledge_repo.create(item1)
        
        # Create document in project 2
        async with pool2.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO documents (id, project_id, name, type, version, content_hash, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                """,
                uuid4(),
                project_id2,
                "project2.md",
                DocumentType.MARKDOWN.value,
                "1.0.0",
                "b" * 64,
            )
            
            # Create knowledge item in project 2 with same query text
            await conn.execute(
                """
                INSERT INTO knowledge_items (id, document_id, chunk_text, chunk_index, embedding, metadata, created_at)
                VALUES ($1, (SELECT id FROM documents WHERE project_id = $2 LIMIT 1), $3, $4, $5, $6, NOW())
                """,
                uuid4(),
                project_id2,
                "Python machine learning frameworks include TensorFlow and PyTorch.",
                0,
                '[' + ','.join(['0.2'] * 1536) + ']',
                '{}',
            )
        
        try:
            # Act - Search in project 1
            results = await knowledge_repo.keyword_search(
                project_id=project_id1,
                query_text="Python machine learning",
                top_k=10
            )
            
            # Assert - Should only return results from project 1
            assert len(results) == 1, "Should only return results from specified project"
            result_item, _ = results[0]
            assert result_item.id == item1_id, "Should only return item from project 1"
            
        finally:
            await cleanup_test_project(pool1, project_id1)
            await cleanup_test_project(pool2, project_id2)

    async def test_keyword_search_respects_top_k_limit(self):
        """Test keyword_search respects the top_k parameter."""
        # Arrange
        pool, project_id = await create_test_project()
        doc_repo = DocumentRepository(pool)
        knowledge_repo = KnowledgeRepository(pool)
        
        now = datetime.now(timezone.utc)
        
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
        
        # Create 5 knowledge items all matching query "data"
        for i in range(5):
            item = KnowledgeItem(
                id=uuid4(),
                document_id=doc_id,
                chunk_text=f"Data science and data analysis are important for data-driven decisions. Chunk {i}",
                chunk_index=i,
                embedding=[0.1 * i] * 1536,
                metadata={"index": i},
                created_at=now,
            )
            await knowledge_repo.create(item)
        
        try:
            # Act - Search with top_k=3
            results = await knowledge_repo.keyword_search(
                project_id=project_id,
                query_text="data",
                top_k=3
            )
            
            # Assert
            assert len(results) == 3, "Should return exactly top_k results"
            
            # Verify scores are ordered descending
            scores = [score for _, score in results]
            assert scores == sorted(scores, reverse=True), "Scores should be ordered descending"
            
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_keyword_search_returns_empty_for_no_matches(self):
        """Test keyword_search returns empty list when no documents match."""
        # Arrange
        pool, project_id = await create_test_project()
        doc_repo = DocumentRepository(pool)
        knowledge_repo = KnowledgeRepository(pool)
        
        now = datetime.now(timezone.utc)
        
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
        
        # Create knowledge item with no matching keywords
        item = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="This content is about completely different topics.",
            chunk_index=0,
            embedding=[0.1] * 1536,
            metadata={},
            created_at=now,
        )
        await knowledge_repo.create(item)
        
        try:
            # Act - Search for non-existent query
            results = await knowledge_repo.keyword_search(
                project_id=project_id,
                query_text="quantum physics cryptography",
                top_k=10
            )
            
            # Assert
            assert len(results) == 0, "Should return empty list when no matches found"
            assert results == [], "Result should be empty list"
            
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_keyword_search_returns_empty_for_project_with_no_documents(self):
        """Test keyword_search returns empty list for project with no documents."""
        # Arrange
        pool, project_id = await create_test_project()
        knowledge_repo = KnowledgeRepository(pool)
        
        try:
            # Act - Search in empty project
            results = await knowledge_repo.keyword_search(
                project_id=project_id,
                query_text="machine learning",
                top_k=10
            )
            
            # Assert
            assert len(results) == 0, "Should return empty list for project with no documents"
            assert results == [], "Result should be empty list"
            
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_keyword_search_bm25_scores_properly_computed(self):
        """Test BM25 scores are properly computed and ordered."""
        # Arrange
        pool, project_id = await create_test_project()
        doc_repo = DocumentRepository(pool)
        knowledge_repo = KnowledgeRepository(pool)
        
        now = datetime.now(timezone.utc)
        
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
        
        # Create items with varying relevance
        # Item 1: Query appears 3 times
        item1 = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Python Python Python programming language",
            chunk_index=0,
            embedding=[0.1] * 1536,
            metadata={},
            created_at=now,
        )
        
        # Item 2: Query appears 1 time
        item2 = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Python is a versatile programming language",
            chunk_index=1,
            embedding=[0.2] * 1536,
            metadata={},
            created_at=now,
        )
        
        await knowledge_repo.create(item1)
        await knowledge_repo.create(item2)
        
        try:
            # Act
            results = await knowledge_repo.keyword_search(
                project_id=project_id,
                query_text="Python",
                top_k=10
            )
            
            # Assert
            assert len(results) == 2, "Should return 2 results"
            
            # Extract scores
            score1 = results[0][1]
            score2 = results[1][1]
            
            # Item with more occurrences should have higher score
            assert score1 > score2, "Item with more query occurrences should have higher BM25 score"
            
            # Both scores should be positive
            assert score1 > 0, "BM25 score should be positive"
            assert score2 > 0, "BM25 score should be positive"
            
            # Scores should be floats
            assert isinstance(score1, float), "Score should be float type"
            assert isinstance(score2, float), "Score should be float type"
            
        finally:
            await cleanup_test_project(pool, project_id)

    async def test_keyword_search_handles_multi_word_queries(self):
        """Test keyword_search handles multi-word natural language queries."""
        # Arrange
        pool, project_id = await create_test_project()
        doc_repo = DocumentRepository(pool)
        knowledge_repo = KnowledgeRepository(pool)
        
        now = datetime.now(timezone.utc)
        
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
        
        # Create items
        # Item 1: Contains both "neural" and "network"
        item1 = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Neural networks are a type of machine learning model inspired by biological neural systems.",
            chunk_index=0,
            embedding=[0.1] * 1536,
            metadata={},
            created_at=now,
        )
        
        # Item 2: Contains only "network"
        item2 = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Computer network protocols enable communication between devices.",
            chunk_index=1,
            embedding=[0.2] * 1536,
            metadata={},
            created_at=now,
        )
        
        # Item 3: Contains neither
        item3 = KnowledgeItem(
            id=uuid4(),
            document_id=doc_id,
            chunk_text="Data structures and algorithms are fundamental to programming.",
            chunk_index=2,
            embedding=[0.3] * 1536,
            metadata={},
            created_at=now,
        )
        
        await knowledge_repo.create(item1)
        await knowledge_repo.create(item2)
        await knowledge_repo.create(item3)
        
        try:
            # Act - Search with multi-word query
            results = await knowledge_repo.keyword_search(
                project_id=project_id,
                query_text="neural network",
                top_k=10
            )
            
            # Assert
            assert len(results) >= 1, "Should return at least 1 matching result"
            
            # First result should contain both words (highest relevance)
            first_item, first_score = results[0]
            assert "neural" in first_item.chunk_text.lower(), "Top result should contain 'neural'"
            assert "network" in first_item.chunk_text.lower(), "Top result should contain 'network'"
            assert first_score > 0, "BM25 score should be positive"
            
        finally:
            await cleanup_test_project(pool, project_id)
