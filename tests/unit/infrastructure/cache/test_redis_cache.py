"""Unit tests for RedisCacheService."""

import hashlib
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.infrastructure.cache.redis_cache import RedisCacheService


@pytest.fixture
def redis_url():
    """Redis connection URL for testing."""
    return "redis://localhost:6379/0"


@pytest.fixture
def cache_service(redis_url):
    """Create RedisCacheService instance."""
    return RedisCacheService(redis_url=redis_url)


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client with async methods."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)
    mock_client.setex = AsyncMock(return_value=None)
    mock_client.delete = AsyncMock(return_value=None)
    mock_client.close = AsyncMock(return_value=None)
    return mock_client


@pytest.mark.asyncio
async def test_generate_cache_key_consistency(cache_service):
    """Test cache key generation is consistent for identical inputs."""
    # Arrange
    project_id = uuid4()
    query_text = "machine learning algorithms"
    use_hybrid = True
    use_rerank = False
    top_k = 10
    prefix = "rag:query:"

    # Act
    key1 = cache_service.generate_cache_key(
        project_id, query_text, use_hybrid, use_rerank, top_k, prefix
    )
    key2 = cache_service.generate_cache_key(
        project_id, query_text, use_hybrid, use_rerank, top_k, prefix
    )

    # Assert
    assert key1 == key2, "Same inputs should generate identical keys"
    assert prefix in key1, "Key should contain prefix"
    assert str(project_id) in key1, "Key should contain project_id"


@pytest.mark.asyncio
async def test_generate_cache_key_uniqueness(cache_service):
    """Test cache keys are unique for different parameters."""
    # Arrange
    project_id = uuid4()
    query_text = "machine learning algorithms"
    prefix = "rag:query:"

    # Act - Generate keys with different parameters
    key1 = cache_service.generate_cache_key(
        project_id, query_text, True, True, 10, prefix
    )
    key2 = cache_service.generate_cache_key(
        project_id, query_text, True, False, 10, prefix  # Different use_rerank
    )
    key3 = cache_service.generate_cache_key(
        project_id, query_text, False, True, 10, prefix  # Different use_hybrid
    )
    key4 = cache_service.generate_cache_key(
        project_id, query_text, True, True, 20, prefix  # Different top_k
    )
    key5 = cache_service.generate_cache_key(
        project_id, "different query", True, True, 10, prefix  # Different query
    )

    # Assert
    keys = [key1, key2, key3, key4, key5]
    assert len(keys) == len(set(keys)), "All keys should be unique"


@pytest.mark.asyncio
async def test_generate_cache_key_format(cache_service):
    """Test cache key format matches specification."""
    # Arrange
    project_id = uuid4()
    query_text = "test query"
    use_hybrid = True
    use_rerank = False
    top_k = 5
    prefix = "rag:query:"

    # Act
    key = cache_service.generate_cache_key(
        project_id, query_text, use_hybrid, use_rerank, top_k, prefix
    )

    # Assert - Format: {prefix}{project_id}:{hash}:{use_hybrid}:{use_rerank}:{top_k}
    parts = key.split(":")
    assert len(parts) >= 6, "Key should have at least 6 parts separated by colons"
    assert key.startswith(prefix), f"Key should start with prefix '{prefix}'"
    assert str(project_id) in key, "Key should contain project_id"
    assert "True" in key, "Key should contain use_hybrid flag"
    assert "False" in key, "Key should contain use_rerank flag"
    assert "5" in key, "Key should contain top_k value"


@pytest.mark.asyncio
async def test_generate_cache_key_sha256_hash(cache_service):
    """Test cache key uses SHA256 hash truncated to 16 chars."""
    # Arrange
    project_id = uuid4()
    query_text = "machine learning"
    expected_hash = hashlib.sha256(query_text.encode()).hexdigest()[:16]
    prefix = "rag:query:"

    # Act
    key = cache_service.generate_cache_key(
        project_id, query_text, True, True, 10, prefix
    )

    # Assert
    assert expected_hash in key, "Key should contain SHA256 hash (16 chars)"


@pytest.mark.asyncio
async def test_get_cache_hit(cache_service, mock_redis_client):
    """Test successful cache retrieval (cache hit)."""
    # Arrange
    cache_key = "rag:query:test-key"
    cached_value = '{"results": ["chunk1", "chunk2"]}'
    mock_redis_client.get.return_value = cached_value

    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch("redis.asyncio.from_url", side_effect=mock_from_url):
        # Act
        result = await cache_service.get(cache_key)

        # Assert
        assert result == cached_value, "Should return cached value"
        mock_redis_client.get.assert_awaited_once_with(cache_key)


@pytest.mark.asyncio
async def test_get_cache_miss(cache_service, mock_redis_client):
    """Test cache retrieval when key doesn't exist (cache miss)."""
    # Arrange
    cache_key = "rag:query:nonexistent-key"
    mock_redis_client.get.return_value = None

    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch("redis.asyncio.from_url", side_effect=mock_from_url):
        # Act
        result = await cache_service.get(cache_key)

        # Assert
        assert result is None, "Should return None for cache miss"
        mock_redis_client.get.assert_awaited_once_with(cache_key)


@pytest.mark.asyncio
async def test_get_redis_error_handling(cache_service, mock_redis_client):
    """Test graceful error handling when Redis GET fails."""
    # Arrange
    cache_key = "rag:query:test-key"
    mock_redis_client.get.side_effect = Exception("Redis connection error")

    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch("redis.asyncio.from_url", side_effect=mock_from_url):
        # Act
        result = await cache_service.get(cache_key)

        # Assert
        assert result is None, "Should return None on Redis error (graceful degradation)"
        mock_redis_client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_successful(cache_service, mock_redis_client):
    """Test successful cache value storage."""
    # Arrange
    cache_key = "rag:query:test-key"
    cache_value = '{"results": ["chunk1"]}'
    ttl = 3600

    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch("redis.asyncio.from_url", side_effect=mock_from_url):
        # Act
        await cache_service.set(cache_key, cache_value, ttl)

        # Assert
        mock_redis_client.setex.assert_awaited_once_with(cache_key, ttl, cache_value)


@pytest.mark.asyncio
async def test_set_with_custom_ttl(cache_service, mock_redis_client):
    """Test cache storage with custom TTL value."""
    # Arrange
    cache_key = "rag:query:test-key"
    cache_value = '{"results": []}'
    custom_ttl = 7200  # 2 hours

    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch("redis.asyncio.from_url", side_effect=mock_from_url):
        # Act
        await cache_service.set(cache_key, cache_value, custom_ttl)

        # Assert
        mock_redis_client.setex.assert_awaited_once_with(cache_key, custom_ttl, cache_value)


@pytest.mark.asyncio
async def test_set_redis_error_handling(cache_service, mock_redis_client):
    """Test graceful error handling when Redis SET fails."""
    # Arrange
    cache_key = "rag:query:test-key"
    cache_value = '{"results": []}'
    ttl = 3600
    mock_redis_client.setex.side_effect = Exception("Redis write error")

    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch("redis.asyncio.from_url", side_effect=mock_from_url):
        # Act - Should not raise exception
        await cache_service.set(cache_key, cache_value, ttl)

        # Assert
        mock_redis_client.setex.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_successful(cache_service, mock_redis_client):
    """Test successful cache key deletion."""
    # Arrange
    cache_key = "rag:query:test-key"

    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch("redis.asyncio.from_url", side_effect=mock_from_url):
        # Act
        await cache_service.delete(cache_key)

        # Assert
        mock_redis_client.delete.assert_awaited_once_with(cache_key)


@pytest.mark.asyncio
async def test_delete_redis_error_handling(cache_service, mock_redis_client):
    """Test graceful error handling when Redis DELETE fails."""
    # Arrange
    cache_key = "rag:query:test-key"
    mock_redis_client.delete.side_effect = Exception("Redis delete error")

    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch("redis.asyncio.from_url", side_effect=mock_from_url):
        # Act - Should not raise exception
        await cache_service.delete(cache_key)

        # Assert
        mock_redis_client.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_client_reuse(cache_service):
    """Test Redis client is created once and reused."""
    # Arrange
    cache_key = "rag:query:test-key"
    call_count = 0

    async def mock_from_url(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        return mock_client

    with patch("redis.asyncio.from_url", side_effect=mock_from_url):
        # Act - Call get multiple times
        await cache_service.get(cache_key)
        await cache_service.get(cache_key)
        await cache_service.get(cache_key)

        # Assert - from_url should only be called once (client reused)
        assert call_count == 1, "Redis client should be created once and reused"


@pytest.mark.asyncio
async def test_close_connection(cache_service, mock_redis_client):
    """Test Redis connection close."""
    # Arrange
    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch("redis.asyncio.from_url", side_effect=mock_from_url):
        await cache_service.get("test-key")  # Initialize client

        # Act
        await cache_service.close()

        # Assert
        mock_redis_client.aclose.assert_awaited_once()
        assert cache_service._client is None, "Client should be set to None after close"
