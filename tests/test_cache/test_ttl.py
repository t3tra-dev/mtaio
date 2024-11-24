"""
Test TTL cache implementation.
"""

import pytest
import asyncio
from mtaio.cache import TTLCache, TTLLRUCache


@pytest.mark.asyncio
async def test_ttl_cache_basic():
    """Test basic TTL cache operations."""
    cache = TTLCache[str](default_ttl=1.0)
    await cache.start()

    # Test set and get
    await cache.set("key1", "value1")
    assert await cache.get("key1") == "value1"

    # Test expiration
    await asyncio.sleep(1.1)
    assert await cache.get("key1") is None

    await cache.stop()


@pytest.mark.asyncio
async def test_ttl_cache_max_size():
    """Test TTL cache size limit."""
    cache = TTLLRUCache[str](max_size=2)
    await cache.start()

    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    await cache.set("key3", "value3")  # Should evict key1

    assert await cache.get("key1") is None
    assert await cache.get("key2") == "value2"
    assert await cache.get("key3") == "value3"

    await cache.stop()
