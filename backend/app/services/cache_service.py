"""
Cache service for price and quote caching with Redis.

Provides specialized caching functions for asset prices with
configurable TTL and automatic serialization.
"""

from decimal import Decimal
from uuid import UUID

from app.core.logging import get_logger
from app.core.redis import get_redis, RedisCache

logger = get_logger(__name__)

# Default TTL for price cache (5 minutes)
DEFAULT_PRICE_TTL = 300

# Cache key prefixes
PRICE_PREFIX = "price"
PRICES_BATCH_PREFIX = "prices_batch"


class PriceCacheService:
    """Service for caching asset prices in Redis."""

    def __init__(self, prefix: str = "investctr"):
        self.prefix = prefix
        self._cache = RedisCache(prefix=prefix)

    def _price_key(self, asset_id: UUID) -> str:
        """Generate cache key for a single asset price."""
        return f"{PRICE_PREFIX}:{str(asset_id)}"

    async def get_cached_price(
        self,
        asset_id: UUID,
    ) -> Decimal | None:
        """
        Get cached price for an asset.

        Args:
            asset_id: Asset UUID

        Returns:
            Cached price as Decimal or None if not cached
        """
        try:
            key = self._price_key(asset_id)
            value = await self._cache.get(key)

            if value is not None:
                logger.debug("cache_hit", asset_id=str(asset_id))
                return Decimal(value)

            logger.debug("cache_miss", asset_id=str(asset_id))
            return None
        except Exception as e:
            logger.warning(
                "cache_get_error",
                asset_id=str(asset_id),
                error=str(e),
            )
            return None

    async def set_cached_price(
        self,
        asset_id: UUID,
        price: Decimal,
        ttl: int = DEFAULT_PRICE_TTL,
    ) -> bool:
        """
        Cache a price for an asset.

        Args:
            asset_id: Asset UUID
            price: Price to cache
            ttl: Time-to-live in seconds (default 300 = 5 minutes)

        Returns:
            True if cached successfully, False otherwise
        """
        try:
            key = self._price_key(asset_id)
            # Store as string to preserve Decimal precision
            await self._cache.set(key, str(price), expire_seconds=ttl)

            logger.debug(
                "cache_set",
                asset_id=str(asset_id),
                price=str(price),
                ttl=ttl,
            )
            return True
        except Exception as e:
            logger.warning(
                "cache_set_error",
                asset_id=str(asset_id),
                error=str(e),
            )
            return False

    async def delete_cached_price(
        self,
        asset_id: UUID,
    ) -> bool:
        """
        Delete cached price for an asset.

        Args:
            asset_id: Asset UUID

        Returns:
            True if deleted successfully
        """
        try:
            key = self._price_key(asset_id)
            await self._cache.delete(key)
            logger.debug("cache_delete", asset_id=str(asset_id))
            return True
        except Exception as e:
            logger.warning(
                "cache_delete_error",
                asset_id=str(asset_id),
                error=str(e),
            )
            return False

    async def get_cached_prices(
        self,
        asset_ids: list[UUID],
    ) -> dict[UUID, Decimal]:
        """
        Get cached prices for multiple assets.

        Args:
            asset_ids: List of asset UUIDs

        Returns:
            Dictionary mapping asset_id -> price for cached items
        """
        if not asset_ids:
            return {}

        prices: dict[UUID, Decimal] = {}
        try:
            client = await get_redis()

            # Build keys
            keys = [f"{self.prefix}:{self._price_key(aid)}" for aid in asset_ids]

            # Use MGET for efficient batch retrieval
            values = await client.mget(keys)

            for asset_id, value in zip(asset_ids, values):
                if value is not None:
                    prices[asset_id] = Decimal(value)

            logger.debug(
                "cache_batch_get",
                requested=len(asset_ids),
                found=len(prices),
            )
        except Exception as e:
            logger.warning("cache_batch_get_error", error=str(e))

        return prices

    async def set_cached_prices(
        self,
        prices: dict[UUID, Decimal],
        ttl: int = DEFAULT_PRICE_TTL,
    ) -> bool:
        """
        Cache multiple prices at once.

        Args:
            prices: Dictionary mapping asset_id -> price
            ttl: Time-to-live in seconds

        Returns:
            True if cached successfully
        """
        if not prices:
            return True

        try:
            client = await get_redis()

            # Use pipeline for efficient batch operations
            pipe = client.pipeline()

            for asset_id, price in prices.items():
                key = f"{self.prefix}:{self._price_key(asset_id)}"
                pipe.set(key, str(price), ex=ttl)

            await pipe.execute()

            logger.debug(
                "cache_batch_set",
                count=len(prices),
                ttl=ttl,
            )
            return True
        except Exception as e:
            logger.warning("cache_batch_set_error", error=str(e))
            return False


# Convenience functions using default cache instance
_price_cache = PriceCacheService()


async def get_cached_price(asset_id: UUID) -> Decimal | None:
    """
    Get cached price for an asset.

    Args:
        asset_id: Asset UUID

    Returns:
        Cached price or None if not cached
    """
    return await _price_cache.get_cached_price(asset_id)


async def set_cached_price(
    asset_id: UUID,
    price: Decimal,
    ttl: int = DEFAULT_PRICE_TTL,
) -> bool:
    """
    Cache a price for an asset.

    Args:
        asset_id: Asset UUID
        price: Price to cache
        ttl: Time-to-live in seconds (default 300 = 5 minutes)

    Returns:
        True if cached successfully
    """
    return await _price_cache.set_cached_price(asset_id, price, ttl)


async def get_cached_prices(asset_ids: list[UUID]) -> dict[UUID, Decimal]:
    """
    Get cached prices for multiple assets.

    Args:
        asset_ids: List of asset UUIDs

    Returns:
        Dictionary mapping asset_id -> price for cached items
    """
    return await _price_cache.get_cached_prices(asset_ids)


async def set_cached_prices(
    prices: dict[UUID, Decimal],
    ttl: int = DEFAULT_PRICE_TTL,
) -> bool:
    """
    Cache multiple prices at once.

    Args:
        prices: Dictionary mapping asset_id -> price
        ttl: Time-to-live in seconds

    Returns:
        True if cached successfully
    """
    return await _price_cache.set_cached_prices(prices, ttl)
