# Basic Usage

This guide covers the fundamental features of mtaio through practical examples.

## Core Functionality

### Task Execution

The `TaskExecutor` provides controlled execution of asynchronous tasks:

```python
from mtaio.core import TaskExecutor

async def process_item(item: str) -> str:
    return f"Processed: {item}"

async def main():
    # Basic usage
    async with TaskExecutor() as executor:
        # Process single task
        result = await executor.run(process_item("data"))
        
        # Process multiple tasks with concurrency limit
        items = ["item1", "item2", "item3", "item4"]
        results = await executor.gather(
            *(process_item(item) for item in items),
            limit=2  # Maximum 2 concurrent tasks
        )

    # Map operation across items
    async with TaskExecutor() as executor:
        results = await executor.map(process_item, items, limit=2)
```

### Async Queue

For managing asynchronous data flow:

```python
from mtaio.core import AsyncQueue

async def producer_consumer():
    queue = AsyncQueue[str](maxsize=10)
    
    # Producer
    await queue.put("item")
    
    # Consumer
    item = await queue.get()
    queue.task_done()
    
    # Wait for all tasks to complete
    await queue.join()
```

## Event Handling

The event system allows for decoupled communication between components:

```python
from mtaio.events import EventEmitter

# Create emitter
emitter = EventEmitter()

# Define handlers
@emitter.on("user_action")
async def handle_user_action(event):
    user = event.data
    print(f"User {user['name']} performed action")

@emitter.once("startup")  # One-time handler
async def handle_startup(event):
    print("Application started")

# Emit events
await emitter.emit("startup", {"time": "2024-01-01"})
await emitter.emit("user_action", {"name": "John"})
```

## Caching

mtaio provides various caching mechanisms:

### TTL Cache

```python
from mtaio.cache import TTLCache

# Create cache with 5-minute TTL
cache = TTLCache[str](
    default_ttl=300.0,
    max_size=1000
)

# Basic operations
await cache.set("key", "value")
value = await cache.get("key")

# With custom TTL
await cache.set("key2", "value2", ttl=60.0)  # 60 seconds

# Batch operations
await cache.set_many({
    "key1": "value1",
    "key2": "value2"
})
```

### Distributed Cache

```python
from mtaio.cache import DistributedCache

# Create distributed cache with multiple nodes
cache = DistributedCache[str](
    nodes=[
        ("localhost", 5000),
        ("localhost", 5001)
    ],
    replication_factor=2
)

async with cache:
    await cache.set("key", "value")
    value = await cache.get("key")
```

## Resource Management

### Rate Limiting

```python
from mtaio.resources import RateLimiter

# Create rate limiter
limiter = RateLimiter(10.0)  # 10 operations per second

@limiter.limit
async def rate_limited_operation():
    # This function is limited to 10 calls per second
    pass

# Manual rate limiting
async def manual_rate_limit():
    async with limiter:
        # Rate-limited code block
        pass
```

### Timeout Management

```python
from mtaio.resources import TimeoutManager

async def operation_with_timeout():
    async with TimeoutManager(5.0) as tm:  # 5 seconds timeout
        result = await tm.run(long_running_operation())
        
        # Different timeout for specific operation
        result2 = await tm.run(
            another_operation(),
            timeout=2.0  # 2 seconds timeout
        )
```

## Error Handling

mtaio provides a comprehensive exception hierarchy:

```python
from mtaio.exceptions import (
    MTAIOError,
    TimeoutError,
    CacheError,
    RateLimitError
)

async def safe_operation():
    try:
        await rate_limited_operation()
    except RateLimitError:
        # Handle rate limit exceeded
        pass
    except TimeoutError:
        # Handle timeout
        pass
    except MTAIOError as e:
        # Handle any mtaio-specific error
        print(f"Operation failed: {e}")
```

## Type Safety

mtaio is fully typed and supports type checking:

```python
from mtaio.typing import AsyncFunc, CacheKey, CacheValue

class CustomCache(CacheValue):
    def __init__(self, data: str):
        self.data = data
    
    async def serialize(self) -> bytes:
        return self.data.encode()
    
    @classmethod
    async def deserialize(cls, data: bytes) -> 'CustomCache':
        return cls(data.decode())

# Type-safe function definition
async def process_data(func: AsyncFunc[str]) -> str:
    return await func()
```

## Common Patterns

### Chain Operations

```python
from mtaio.data import Pipeline
from mtaio.events import EventEmitter

# Create processing pipeline
pipeline = Pipeline()
emitter = EventEmitter()

# Add processing stages
pipeline.add_stage(DataValidationStage())
pipeline.add_stage(DataTransformStage())
pipeline.add_stage(DataStorageStage())

# Process data with events
async def process():
    async with pipeline:
        for item in items:
            result = await pipeline.process(item)
            await emitter.emit("item_processed", result)
```

### Monitoring

```python
from mtaio.monitoring import ResourceMonitor

# Create monitor
monitor = ResourceMonitor(interval=1.0)

@monitor.on_threshold_exceeded
async def handle_threshold(metric: str, value: float, threshold: float):
    print(f"Alert: {metric} exceeded threshold: {value} > {threshold}")

# Start monitoring
await monitor.start()
monitor.set_threshold("cpu_usage", 80.0)  # 80% CPU threshold
```

## Next Steps

Once you're comfortable with these basics, you can:

1. Explore [Advanced Usage](advanced-usage.md) for more complex patterns
2. Check the [API Reference](../api/index.md) for detailed documentation
3. See our [examples repository](https://github.com/t3tra-dev/mtaio/tree/main/examples) for more examples
