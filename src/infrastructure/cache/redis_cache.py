"""Redis cache service for RAG query result caching."""

import hashlib
import logging
from typing import Optional
from uuid import UUID

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisCacheService:
    """Service for caching RAG query results in Redis."""

    def __init__(self, redis_url: str):
        """Initialize Redis cache service.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
        """
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client.

        Returns:
            Redis async client instance
        """
        if self._client is None:
            self._client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def get(self, key: str) -> Optional[str]:
        """Retrieve cached value from Redis.

        Args:
            key: Cache key

        Returns:
            Cached value as string, or None if not found or error occurs
        """
        try:
            client = await self._get_client()
            value = await client.get(key)
            if value:
                logger.debug(f"Cache HIT for key: {key}")
            else:
                logger.debug(f"Cache MISS for key: {key}")
            return value
        except Exception as e:
            logger.warning(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int) -> None:
        """Store value in Redis with TTL.

        Args:
            key: Cache key
            value: Value to cache (string)
            ttl: Time-to-live in seconds
        """
        try:
            client = await self._get_client()
            await client.setex(key, ttl, value)
            logger.debug(f"Cache SET for key: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"Redis SET error for key {key}: {e}")

    async def delete(self, key: str) -> None:
        """Delete cache entry.

        Args:
            key: Cache key to delete
        """
        try:
            client = await self._get_client()
            await client.delete(key)
            logger.debug(f"Cache DELETE for key: {key}")
        except Exception as e:
            logger.warning(f"Redis DELETE error for key {key}: {e}")

    def generate_cache_key(
        self,
        project_id: UUID,
        query_text: str,
        use_hybrid: bool,
        use_rerank: bool,
        top_k: int,
        prefix: str,
    ) -> str:
        """Generate consistent cache key for RAG query.

        Uses SHA256 hash of query text for consistent, collision-resistant keys.

        Args:
            project_id: Project UUID
            query_text: Query text
            use_hybrid: Whether hybrid search is enabled
            use_rerank: Whether re-ranking is enabled
            top_k: Number of results requested
            prefix: Cache key prefix from settings

        Returns:
            Generated cache key string
        """
        # Hash query text for consistent key generation
        query_hash = hashlib.sha256(query_text.encode()).hexdigest()[:16]

        # Build cache key
        key = f"{prefix}{project_id}:{query_hash}:{use_hybrid}:{use_rerank}:{top_k}"
        return key

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
