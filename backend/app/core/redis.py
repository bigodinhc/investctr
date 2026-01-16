"""
Redis client and utilities.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as redis

from app.config import settings


def get_redis_url() -> str:
    """Get Redis URL from settings."""
    if settings.redis_url:
        return str(settings.redis_url)
    return "redis://localhost:6379/0"


# Async Redis client
_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            get_redis_url(),
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


async def redis_health_check() -> bool:
    """Check if Redis is healthy."""
    try:
        client = await get_redis()
        await client.ping()
        return True
    except Exception:
        return False


@asynccontextmanager
async def redis_connection() -> AsyncGenerator[redis.Redis, None]:
    """Context manager for Redis connection."""
    client = await get_redis()
    try:
        yield client
    finally:
        pass  # Connection pooling handles cleanup


# Cache utilities
class RedisCache:
    """Simple Redis cache wrapper."""

    def __init__(self, prefix: str = "investctr"):
        self.prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        client = await get_redis()
        return await client.get(self._key(key))

    async def set(
        self,
        key: str,
        value: str,
        expire_seconds: int | None = None,
    ) -> None:
        """Set value in cache with optional expiration."""
        client = await get_redis()
        await client.set(self._key(key), value, ex=expire_seconds)

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        client = await get_redis()
        await client.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        client = await get_redis()
        return bool(await client.exists(self._key(key)))


# Default cache instance
cache = RedisCache()
