"""
Cache usage examples for mtaio library.

This example demonstrates:
- Basic TTL cache operations
- Distributed cache usage
- Cache eviction policies
- Error handling
"""

import asyncio
from mtaio.cache import (
    TTLCache,
    TTLLRUCache,
    DistributedCache,
)
from mtaio.exceptions import CacheError


async def basic_cache_example() -> None:
    """
    Demonstrates basic TTL cache operations.
    """
    # Create cache with 5-minute TTL
    cache = TTLCache[str](default_ttl=300.0, max_size=1000)  # 5 minutes

    # Basic set/get operations
    await cache.set("user:1", "John Doe")
    await cache.set("user:2", "Jane Doe", ttl=60.0)  # Custom TTL

    # Get values
    user1 = await cache.get("user:1")
    user2 = await cache.get("user:2")
    print(f"Users: {user1}, {user2}")

    # Batch operations
    users = {"user:3": "Alice", "user:4": "Bob"}
    await cache.set_many(users)

    # Get multiple values
    results = await cache.get_many(["user:3", "user:4"])
    print(f"Batch results: {results}")


async def lru_cache_example() -> None:
    """
    Demonstrates LRU cache with size limits.
    """
    # Create LRU cache with max size
    cache = TTLLRUCache[str](
        max_size=3, default_ttl=60.0  # Only keeps 3 most recently used items
    )

    # Add items
    items = ["item1", "item2", "item3", "item4"]
    for i, item in enumerate(items):
        await cache.set(f"key:{i}", item)
        current_items = await cache.items()
        print(f"Cache after adding {item}: {dict(current_items)}")


async def distributed_cache_example() -> None:
    """
    Demonstrates distributed cache operations.
    """
    # Create distributed cache with multiple nodes
    cache = DistributedCache[str](
        nodes=[("localhost", 5000), ("localhost", 5001)],
        replication_factor=2,
        read_quorum=1,
    )

    try:
        async with cache:
            # Set and get values
            await cache.set("shared:1", "Distributed Value")
            value = await cache.get("shared:1")
            print(f"Distributed value: {value}")
    except CacheError as e:
        print(f"Cache error: {e}")


async def error_handling_example() -> None:
    """
    Demonstrates cache error handling.
    """
    cache = TTLCache[str]()

    try:
        # Attempt to get non-existent key
        value = await cache.get("nonexistent")
        print(f"Value: {value}")  # Will be None

        # Custom default value
        value = await cache.get("nonexistent", default="Default Value")
        print(f"Value with default: {value}")

    except CacheError as e:
        print(f"Cache operation failed: {e}")


async def main() -> None:
    """
    Run all cache examples.
    """
    print("=== Basic Cache Example ===")
    await basic_cache_example()

    print("\n=== LRU Cache Example ===")
    await lru_cache_example()

    print("\n=== Distributed Cache Example ===")
    await distributed_cache_example()

    print("\n=== Error Handling Example ===")
    await error_handling_example()


if __name__ == "__main__":
    asyncio.run(main())
