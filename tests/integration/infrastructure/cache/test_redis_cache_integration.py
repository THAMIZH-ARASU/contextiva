"""Integration tests for RedisCacheService with real Redis."""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from src.infrastructure.cache.redis_cache import RedisCacheService


# Real Redis connection (assumes Docker Redis container on contextiva_default network)
REDIS_URL = "redis://172.21.0.3:6379/0"  # Adjust IP if needed


@pytest.fixture
async def redis_cache():
    """Real Redis cache service for integration tests."""
    cache = RedisCacheService(redis_url=REDIS_URL)
    yield cache
    # Cleanup: Close connection after test
    await cache.close()


@pytest.fixture
async def clean_cache(redis_cache):
    """Ensure Redis is clean before each test."""
    # Flush test keys before test
    if redis_cache._client:
        await redis_cache._client.flushdb()
    yield
    # Flush after test as well
    if redis_cache._client:
        await redis_cache._client.flushdb()


@pytest.mark.asyncio
@pytest.mark.integration
class TestRedisCacheIntegration:
    """Integration tests for Redis caching with real Redis instance."""

    async def test_full_cache_workflow_with_real_redis(self, redis_cache, clean_cache):
        """Test complete cache workflow: set -> get -> delete with real Redis.
        
        This test validates:
        - Successful connection to real Redis
        - Data persistence across operations
        - Cache key generation
        - TTL enforcement
        """
        # Arrange
        project_id = uuid4()
        query_text = "machine learning fundamentals"
        test_value = '{"results": [{"id": "123", "text": "ML basics"}], "total": 1}'
        
        # Generate cache key
        cache_key = redis_cache.generate_cache_key(
            project_id=project_id,
            query_text=query_text,
            use_hybrid=True,
            use_rerank=False,
            top_k=10,
            prefix="test:",
        )
        
        # Act - Set value with TTL
        await redis_cache.set(cache_key, test_value, ttl=60)
        
        # Assert - Get value back
        retrieved_value = await redis_cache.get(cache_key)
        assert retrieved_value == test_value
        
        # Act - Delete value
        await redis_cache.delete(cache_key)
        
        # Assert - Value should be gone
        deleted_value = await redis_cache.get(cache_key)
        assert deleted_value is None

    async def test_cache_ttl_expiration(self, redis_cache, clean_cache):
        """Test that cache entries expire after TTL.
        
        This test validates:
        - TTL is properly set on cache entries
        - Expired entries are not retrievable
        """
        # Arrange
        cache_key = redis_cache.generate_cache_key(
            project_id=uuid4(),
            query_text="test ttl expiration",
            use_hybrid=False,
            use_rerank=False,
            top_k=5,
            prefix="test:",
        )
        test_value = '{"test": "ttl_data"}'
        
        # Act - Set value with very short TTL (2 seconds)
        await redis_cache.set(cache_key, test_value, ttl=2)
        
        # Assert - Value should be retrievable immediately
        immediate_value = await redis_cache.get(cache_key)
        assert immediate_value == test_value
        
        # Act - Wait for TTL to expire
        await asyncio.sleep(3)
        
        # Assert - Value should be gone after TTL
        expired_value = await redis_cache.get(cache_key)
        assert expired_value is None

    async def test_cache_key_uniqueness(self, redis_cache, clean_cache):
        """Test that different query parameters generate unique cache keys.
        
        This test validates:
        - Different project_ids produce different keys
        - Different query texts produce different keys
        - Different flags (use_hybrid, use_rerank) produce different keys
        - Different top_k values produce different keys
        """
        # Arrange
        base_project_id = uuid4()
        base_query = "natural language processing"
        value1 = '{"result": "config1"}'
        value2 = '{"result": "config2"}'
        value3 = '{"result": "config3"}'
        value4 = '{"result": "config4"}'
        
        # Act - Create keys with different parameters
        key1 = redis_cache.generate_cache_key(
            project_id=base_project_id,
            query_text=base_query,
            use_hybrid=True,
            use_rerank=False,
            top_k=10,
            prefix="test:",
        )
        
        key2 = redis_cache.generate_cache_key(
            project_id=uuid4(),  # Different project
            query_text=base_query,
            use_hybrid=True,
            use_rerank=False,
            top_k=10,
            prefix="test:",
        )
        
        key3 = redis_cache.generate_cache_key(
            project_id=base_project_id,
            query_text="different query text",  # Different query
            use_hybrid=True,
            use_rerank=False,
            top_k=10,
            prefix="test:",
        )
        
        key4 = redis_cache.generate_cache_key(
            project_id=base_project_id,
            query_text=base_query,
            use_hybrid=False,  # Different flag
            use_rerank=True,   # Different flag
            top_k=20,          # Different top_k
            prefix="test:",
        )
        
        # Assert - All keys should be unique
        assert key1 != key2, "Different project_ids should produce different keys"
        assert key1 != key3, "Different query texts should produce different keys"
        assert key1 != key4, "Different flags/top_k should produce different keys"
        assert key2 != key3
        assert key2 != key4
        assert key3 != key4
        
        # Act - Store different values with different keys
        await redis_cache.set(key1, value1, ttl=60)
        await redis_cache.set(key2, value2, ttl=60)
        await redis_cache.set(key3, value3, ttl=60)
        await redis_cache.set(key4, value4, ttl=60)
        
        # Assert - Each key retrieves its own value
        assert await redis_cache.get(key1) == value1
        assert await redis_cache.get(key2) == value2
        assert await redis_cache.get(key3) == value3
        assert await redis_cache.get(key4) == value4

    async def test_concurrent_cache_access(self, redis_cache, clean_cache):
        """Test concurrent cache operations (multiple simultaneous queries).
        
        This test validates:
        - Thread safety of cache operations
        - No data corruption during concurrent access
        - All operations complete successfully
        """
        # Arrange
        num_concurrent_operations = 10
        project_id = uuid4()
        
        async def set_and_get(index: int) -> bool:
            """Helper to set and get a cache entry."""
            cache_key = redis_cache.generate_cache_key(
                project_id=project_id,
                query_text=f"concurrent query {index}",
                use_hybrid=index % 2 == 0,
                use_rerank=index % 3 == 0,
                top_k=index,
                prefix="test:",
            )
            value = f'{{"index": {index}, "data": "concurrent_test"}}'
            
            # Set value
            await redis_cache.set(cache_key, value, ttl=60)
            
            # Get value back
            retrieved = await redis_cache.get(cache_key)
            
            # Verify
            return retrieved == value
        
        # Act - Execute concurrent operations
        tasks = [set_and_get(i) for i in range(num_concurrent_operations)]
        results = await asyncio.gather(*tasks)
        
        # Assert - All operations should succeed
        assert all(results), "All concurrent operations should succeed"
        assert len(results) == num_concurrent_operations

    async def test_cache_with_real_json_data(self, redis_cache, clean_cache):
        """Test caching complex JSON data structures (realistic RAG result).
        
        This test validates:
        - Complex nested JSON can be cached and retrieved
        - Data integrity is maintained
        - No serialization issues
        """
        # Arrange - Create realistic RAG query result JSON
        import json
        
        complex_data = {
            "query_id": str(uuid4()),
            "results": [
                {
                    "id": str(uuid4()),
                    "document_id": str(uuid4()),
                    "chunk_text": "Machine learning is a subset of artificial intelligence",
                    "chunk_index": 0,
                    "embedding": [0.1, 0.2, 0.3] * 512,  # 1536 dimensions
                    "metadata": {
                        "source": "textbook",
                        "chapter": 5,
                        "page": 142,
                        "tags": ["ML", "AI", "fundamentals"],
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "similarity_score": 0.95,
                    "bm25_score": 12.5,
                    "rerank_score": 0.98,
                },
                {
                    "id": str(uuid4()),
                    "document_id": str(uuid4()),
                    "chunk_text": "Neural networks are inspired by biological neurons",
                    "chunk_index": 1,
                    "embedding": [0.4, 0.5, 0.6] * 512,
                    "metadata": {
                        "source": "research_paper",
                        "year": 2024,
                        "authors": ["John Doe", "Jane Smith"],
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "similarity_score": 0.87,
                    "bm25_score": 8.3,
                    "rerank_score": 0.92,
                },
            ],
            "total_results": 2,
        }
        
        cache_key = redis_cache.generate_cache_key(
            project_id=uuid4(),
            query_text="machine learning neural networks",
            use_hybrid=True,
            use_rerank=True,
            top_k=10,
            prefix="test:",
        )
        
        serialized_data = json.dumps(complex_data)
        
        # Act - Cache complex data
        await redis_cache.set(cache_key, serialized_data, ttl=60)
        
        # Assert - Retrieve and verify
        retrieved_data = await redis_cache.get(cache_key)
        assert retrieved_data is not None
        
        # Deserialize and compare
        deserialized = json.loads(retrieved_data)
        assert deserialized["query_id"] == complex_data["query_id"]
        assert deserialized["total_results"] == 2
        assert len(deserialized["results"]) == 2
        assert deserialized["results"][0]["chunk_text"] == complex_data["results"][0]["chunk_text"]
        assert deserialized["results"][0]["similarity_score"] == 0.95
        assert deserialized["results"][0]["metadata"]["tags"] == ["ML", "AI", "fundamentals"]

    async def test_cache_connection_error_handling(self):
        """Test graceful degradation when Redis is unavailable.
        
        This test validates:
        - Service handles connection errors gracefully
        - No exceptions are raised to caller
        - Operations return None on failure
        """
        # Arrange - Use invalid Redis URL
        invalid_cache = RedisCacheService(redis_url="redis://invalid_host:9999/0")
        
        cache_key = invalid_cache.generate_cache_key(
            project_id=uuid4(),
            query_text="test query",
            use_hybrid=False,
            use_rerank=False,
            top_k=5,
            prefix="test:",
        )
        
        # Act & Assert - Operations should not raise exceptions
        try:
            # Set should fail gracefully
            await invalid_cache.set(cache_key, "test_value", ttl=60)
            
            # Get should return None
            result = await invalid_cache.get(cache_key)
            assert result is None
            
            # Delete should not raise exception
            await invalid_cache.delete(cache_key)
            
        finally:
            await invalid_cache.close()
