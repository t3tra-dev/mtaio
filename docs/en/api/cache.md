# Cache API Reference

The `mtaio.cache` module provides various caching mechanisms for storing and retrieving data asynchronously.

## Overview

The cache module includes the following main components:

- `TTLCache`: Time-to-live cache implementation
- `DistributedCache`: Distributed caching across multiple nodes
- Various cache policies (LRU, LFU, FIFO)

## TTLCache

`TTLCache[T]` is a generic cache implementation with time-to-live support.

### Basic Usage

```python
from mtaio.cache import TTLCache

# Create cache instance
cache = TTLCache[str](
    default_ttl=300.0,  # 5 minutes TTL
    max_size=1000
)

# Set value
await cache.set("key", "value")

# Get value
value = await cache.get("key")
```

### Class Reference

```python
class TTLCache[T]:
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

        Args:
            default_ttl (float): Default time-to-live in seconds
            max_size (Optional[int]): Maximum cache size (None for unlimited)
            cleanup_interval (float): Cleanup interval in seconds
            eviction_policy (EvictionPolicy): Cache eviction policy
            on_evicted (Optional[Callable[[str, T], Awaitable[None]]]): Callback for evicted items
        """
```

### Methods

#### `async def set(key: str, value: T, ttl: Optional[float] = None) -> None`
Set a cache value with optional TTL override.

```python
# Set with default TTL
await cache.set("key", "value")

# Set with custom TTL
await cache.set("key", "value", ttl=60.0)  # 1 minute TTL
```

#### `async def get(key: str, default: Optional[T] = None) -> Optional[T]`
Get a cache value.

```python
# Get value with default
value = await cache.get("key", default="default_value")

# Check if value exists
if (value := await cache.get("key")) is not None:
    print(f"Found value: {value}")
```

#### `async def delete(key: str) -> None`
Delete a cache value.

```python
await cache.delete("key")
```

#### `async def clear() -> None`
Clear all cache entries.

```python
await cache.clear()
```

#### `async def touch(key: str, ttl: Optional[float] = None) -> bool`
Update item TTL.

```python
# Extend TTL
if await cache.touch("key", ttl=300.0):
    print("TTL updated")
```

#### Batch Operations

```python
# Set multiple values
await cache.set_many({
    "key1": "value1",
    "key2": "value2"
})

# Get multiple values
values = await cache.get_many(["key1", "key2"])

# Delete multiple values
await cache.delete_many(["key1", "key2"])
```

## DistributedCache

`DistributedCache[T]` provides distributed caching across multiple nodes.

### Basic Usage

```python
from mtaio.cache import DistributedCache

# Create distributed cache
cache = DistributedCache[str](
    nodes=[
        ("localhost", 5000),
        ("localhost", 5001)
    ],
    replication_factor=2,
    read_quorum=1
)

async with cache:
    await cache.set("key", "value")
    value = await cache.get("key")
```

### Class Reference

```python
class DistributedCache[T]:
    def __init__(
        self,
        nodes: List[Tuple[str, int]],
        replication_factor: int = 2,
        read_quorum: int = 1,
    ):
        """
        Initialize distributed cache.

        Args:
            nodes (List[Tuple[str, int]]): List of cache node addresses
            replication_factor (int): Number of replicas
            read_quorum (int): Number of nodes for read consensus
        """
```

### Methods

Similar to TTLCache, but with distributed functionality:

#### `async def set(key: str, value: T, ttl: Optional[float] = None) -> None`
Set value across distributed nodes.

```python
await cache.set("key", "value")
```

#### `async def get(key: str) -> Optional[T]`
Get value from distributed cache with quorum.

```python
value = await cache.get("key")
```

## Cache Policies

### EvictionPolicy

Enum defining cache eviction policies:

```python
class EvictionPolicy(Enum):
    LRU = auto()  # Least Recently Used
    LFU = auto()  # Least Frequently Used
    FIFO = auto() # First In First Out
```

### Specialized Cache Classes

#### TTLLRUCache

LRU-specific TTL cache implementation.

```python
from mtaio.cache import TTLLRUCache

cache = TTLLRUCache[str](max_size=1000)
await cache.set("key", "value")
```

#### TTLLFUCache

LFU-specific TTL cache implementation.

```python
from mtaio.cache import TTLLFUCache

cache = TTLLFUCache[str](max_size=1000)
await cache.set("key", "value")
```

#### TTLFIFOCache

FIFO-specific TTL cache implementation.

```python
from mtaio.cache import TTLFIFOCache

cache = TTLFIFOCache[str](max_size=1000)
await cache.set("key", "value")
```

## Statistics and Monitoring

Cache implementations provide statistics tracking:

```python
from mtaio.cache import TTLCache

cache = TTLCache[str]()

# Get cache statistics
stats = cache.get_stats()
print(f"Cache hits: {stats.hits}")
print(f"Cache misses: {stats.misses}")
print(f"Hit rate: {stats.hit_rate:.2f}")
```

### CacheStats Class

```python
@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    items: int = 0
```

## Error Handling

The cache module defines several exception types:

```python
from mtaio.exceptions import (
    CacheError,          # Base cache exception
    CacheKeyError,       # Invalid or not found key
    CacheConnectionError # Connection failure
)

try:
    await cache.get("key")
except CacheKeyError:
    print("Key not found")
except CacheConnectionError:
    print("Connection failed")
except CacheError as e:
    print(f"Cache error: {e}")
```

## Advanced Usage

### Custom Cache Implementations

Creating a custom cache implementation:

```python
from mtaio.cache import TTLCache
from mtaio.typing import CacheKey, CacheValue

class CustomCache(TTLCache[str]):
    async def pre_set(self, key: str, value: str) -> None:
        # Pre-processing before cache set
        pass
    
    async def post_get(self, key: str, value: Optional[str]) -> Optional[str]:
        # Post-processing after cache get
        return value
```

### Cache Decorators

Using cache decorators for function results:

```python
from mtaio.decorators import with_cache
from mtaio.cache import TTLCache

cache = TTLCache[str]()

@with_cache(cache)
async def expensive_operation(param: str) -> str:
    # Expensive computation
    return result
```

## Best Practices

1. **TTL Configuration**
   ```python
   # Short TTL for frequently changing data
   volatile_cache = TTLCache[str](default_ttl=60.0)
   
   # Longer TTL for stable data
   stable_cache = TTLCache[str](default_ttl=3600.0)
   ```

2. **Resource Management**
   ```python
   async with TTLCache[str]() as cache:
       # Cache is automatically cleaned up
       pass
   ```

3. **Error Handling**
   ```python
   try:
       async with cache.transaction() as txn:
           await txn.set("key", "value")
   except CacheError:
       # Handle cache errors
       pass
   ```

4. **Monitoring**
   ```python
   # Monitor cache performance
   stats = cache.get_stats()
   if stats.hit_rate < 0.5:
       logger.warning("Low cache hit rate")
   ```

## See Also

- [Core API Reference](core.md) for base functionality
- [Events API Reference](events.md) for cache events
- [Resources API Reference](resources.md) for resource management
- [Examples Repository](https://github.com/t3tra-dev/mtaio/tree/main/examples/cache.py)
