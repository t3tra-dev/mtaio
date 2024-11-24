"""
TTL (Time To Live) cache implementation.

This module provides components for TTL-based caching:

* TTLCache: Main TTL cache class
* CacheItem: Cache item container
* TTLPolicy: TTL policy implementation
* CacheStats: Cache statistics
"""

from typing import (
    Dict,
    List,
    Optional,
    Any,
    TypeVar,
    Generic,
    Callable,
    Awaitable,
)
from dataclasses import dataclass, field
import asyncio
import time
import logging
from enum import Enum, auto
from collections import OrderedDict

T = TypeVar("T")
logger = logging.getLogger(__name__)


class EvictionPolicy(Enum):
    """Cache eviction policy types."""

    LRU = auto()  # Least Recently Used
    LFU = auto()  # Least Frequently Used
    FIFO = auto()  # First In First Out


@dataclass
class CacheItem(Generic[T]):
    """
    Cache item container.

    :param value: Cached value
    :type value: T
    :param ttl: Time to live in seconds
    :type ttl: float
    :param created_at: Creation timestamp
    :type created_at: float
    :param last_accessed: Last access timestamp
    :type last_accessed: float
    :param access_count: Number of accesses
    :type access_count: int
    """

    value: T
    ttl: float
    created_at: float = field(default_factory=time.monotonic)
    last_accessed: float = field(default_factory=time.monotonic)
    access_count: int = 0

    def is_expired(self) -> bool:
        """Check if item is expired."""
        return time.monotonic() - self.created_at > self.ttl

    def access(self) -> None:
        """Record access to the item."""
        self.last_accessed = time.monotonic()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache statistics container."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    items: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class TTLCache(Generic[T]):
    """
    TTL cache implementation.

    Example::

        cache = TTLCache[str](
            default_ttl=60.0,
            max_size=1000,
            cleanup_interval=30.0
        )

        await cache.set("key", "value", ttl=120.0)
        value = await cache.get("key")
    """

    def __init__(
        self,
        default_ttl: float = 300.0,
        max_size: Optional[int] = None,
        cleanup_interval: float = 60.0,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
        on_evicted: Optional[Callable[[str, T], Awaitable[None]]] = None,
    ):
        """
        Initialize TTL cache.

        :param default_ttl: Default time to live in seconds
        :type default_ttl: float
        :param max_size: Maximum cache size
        :type max_size: Optional[int]
        :param cleanup_interval: Cleanup interval in seconds
        :type cleanup_interval: float
        :param eviction_policy: Cache eviction policy
        :type eviction_policy: EvictionPolicy
        :param on_evicted: Optional callback for evicted items
        :type on_evicted: Optional[Callable[[str, T], Awaitable[None]]]
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        self.eviction_policy = eviction_policy
        self.on_evicted = on_evicted

        self._cache: Dict[str, CacheItem[T]] = {}
        self._access_order: OrderedDict[str, None] = OrderedDict()
        self._stats = CacheStats()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._closed = False

    async def start(self) -> None:
        """Start cache maintenance."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop cache maintenance."""
        self._closed = True
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def set(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """
        Set cache value.

        :param key: Cache key
        :type key: str
        :param value: Value to cache
        :type value: T
        :param ttl: Optional TTL override
        :type ttl: Optional[float]
        """
        async with self._lock:
            if (
                self.max_size
                and len(self._cache) >= self.max_size
                and key not in self._cache
            ):
                await self._evict()

            item = CacheItem(value, ttl or self.default_ttl)
            self._cache[key] = item
            self._access_order[key] = None
            self._stats.items = len(self._cache)

    async def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Get cache value.

        :param key: Cache key
        :type key: str
        :param default: Default value if key not found
        :type default: Optional[T]
        :return: Cached value or default
        :rtype: Optional[T]
        """
        async with self._lock:
            item = self._cache.get(key)

            if item is None:
                self._stats.misses += 1
                return default

            if item.is_expired():
                await self._remove(key)
                self._stats.misses += 1
                self._stats.expirations += 1
                return default

            item.access()
            self._access_order.move_to_end(key)
            self._stats.hits += 1
            return item.value

    async def delete(self, key: str) -> None:
        """
        Delete cache value.

        :param key: Cache key
        :type key: str
        """
        async with self._lock:
            await self._remove(key)

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._stats = CacheStats()

    async def touch(self, key: str, ttl: Optional[float] = None) -> bool:
        """
        Update item TTL.

        :param key: Cache key
        :type key: str
        :param ttl: New TTL value
        :type ttl: Optional[float]
        :return: True if key exists and was touched
        :rtype: bool
        """
        async with self._lock:
            item = self._cache.get(key)
            if item and not item.is_expired():
                item.ttl = ttl or self.default_ttl
                item.created_at = time.monotonic()
                return True
            return False

    async def get_many(
        self, keys: List[str], default: Optional[T] = None
    ) -> Dict[str, Optional[T]]:
        """
        Get multiple cache values.

        :param keys: List of cache keys
        :type keys: List[str]
        :param default: Default value if key not found
        :type default: Optional[T]
        :return: Dictionary of key-value pairs
        :rtype: Dict[str, Optional[T]]
        """
        result = {}
        for key in keys:
            result[key] = await self.get(key, default)
        return result

    async def set_many(self, items: Dict[str, T], ttl: Optional[float] = None) -> None:
        """
        Set multiple cache values.

        :param items: Dictionary of key-value pairs
        :type items: Dict[str, T]
        :param ttl: Optional TTL override
        :type ttl: Optional[float]
        """
        for key, value in items.items():
            await self.set(key, value, ttl)

    async def delete_many(self, keys: List[str]) -> None:
        """
        Delete multiple cache values.

        :param keys: List of cache keys
        :type keys: List[str]
        """
        for key in keys:
            await self.delete(key)

    def get_stats(self) -> CacheStats:
        """
        Get cache statistics.

        :return: Cache statistics
        :rtype: CacheStats
        """
        return self._stats

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of expired items."""
        while not self._closed:
            try:
                async with self._lock:
                    await self._cleanup_expired()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(self.cleanup_interval)

    async def _cleanup_expired(self) -> None:
        """Remove expired items."""
        expired_keys = [key for key, item in self._cache.items() if item.is_expired()]

        for key in expired_keys:
            await self._remove(key)
            self._stats.expirations += 1

    async def _evict(self) -> None:
        """Evict items according to policy."""
        if not self._cache:
            return

        if self.eviction_policy == EvictionPolicy.LRU:
            # Evict least recently used
            key = next(iter(self._access_order))
        elif self.eviction_policy == EvictionPolicy.LFU:
            # Evict least frequently used
            key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
        else:  # FIFO
            # Evict oldest
            key = next(iter(self._access_order))

        await self._remove(key)
        self._stats.evictions += 1

    async def _remove(self, key: str) -> None:
        """Remove item and notify callback."""
        item = self._cache.pop(key, None)
        self._access_order.pop(key, None)
        self._stats.items = len(self._cache)

        if item and self.on_evicted:
            try:
                await self.on_evicted(key, item.value)
            except Exception as e:
                logger.error(f"Error in eviction callback: {e}")

    async def items(self) -> List[tuple[str, T]]:
        """
        Get all non-expired items.

        :return: List of key-value pairs
        :rtype: List[tuple[str, T]]
        """
        async with self._lock:
            return [
                (key, item.value)
                for key, item in self._cache.items()
                if not item.is_expired()
            ]

    async def __aenter__(self) -> "TTLCache[T]":
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.stop()


class TTLLRUCache(TTLCache[T]):
    """
    LRU-specific TTL cache implementation.

    Example::

        cache = TTLLRUCache[str](max_size=1000)
        await cache.set("key", "value")
    """

    def __init__(self, max_size: int, **kwargs: Any):
        """
        Initialize LRU cache.

        :param max_size: Maximum cache size
        :type max_size: int
        """
        super().__init__(
            max_size=max_size, eviction_policy=EvictionPolicy.LRU, **kwargs
        )


class TTLLFUCache(TTLCache[T]):
    """
    LFU-specific TTL cache implementation.

    Example::

        cache = TTLLFUCache[str](max_size=1000)
        await cache.set("key", "value")
    """

    def __init__(self, max_size: int, **kwargs: Any):
        """
        Initialize LFU cache.

        :param max_size: Maximum cache size
        :type max_size: int
        """
        super().__init__(
            max_size=max_size, eviction_policy=EvictionPolicy.LFU, **kwargs
        )


class TTLFIFOCache(TTLCache[T]):
    """
    FIFO-specific TTL cache implementation.

    Example::

        cache = TTLFIFOCache[str](max_size=1000)
        await cache.set("key", "value")
    """

    def __init__(self, max_size: int, **kwargs: Any):
        """
        Initialize FIFO cache.

        :param max_size: Maximum cache size
        :type max_size: int
        """
        super().__init__(
            max_size=max_size, eviction_policy=EvictionPolicy.FIFO, **kwargs
        )
