# Getting Started with mtaio

This guide will help you get started with mtaio framework. We'll cover installation, basic concepts, and create a simple application.

## Installation

First, install mtaio using pip:

```bash
pip install mtaio
```

## Basic Concepts

mtaio is built around several core concepts:

1. **Async-First**: Everything is designed to work with Python's `asyncio`
2. **Resource Management**: Built-in tools for handling system resources efficiently
3. **Event-Driven**: Event-based architecture for building reactive applications
4. **Type Safety**: Full type hints support for better development experience

## Your First mtaio Application

Let's create a simple application that demonstrates the basic features of mtaio.

```python
import asyncio
from mtaio.events import EventEmitter
from mtaio.cache import TTLCache
from mtaio.core import TaskExecutor

# Create a data processor class
class DataProcessor:
    def __init__(self):
        self.emitter = EventEmitter()
        self.cache = TTLCache[str](default_ttl=60.0)  # 60 seconds TTL
        self.executor = TaskExecutor()

    async def process_data(self, data: str) -> str:
        # Check cache first
        cached_result = await self.cache.get(data)
        if cached_result is not None:
            await self.emitter.emit("cache_hit", data)
            return cached_result

        # Process data
        async with self.executor as executor:
            result = await executor.run(self.compute_result, data)

        # Cache the result
        await self.cache.set(data, result)
        await self.emitter.emit("process_complete", result)
        return result

    async def compute_result(self, data: str) -> str:
        # Simulate some heavy computation
        await asyncio.sleep(1)
        return data.upper()

# Create event handlers
async def handle_cache_hit(event):
    print(f"Cache hit for data: {event.data}")

async def handle_process_complete(event):
    print(f"Processing completed with result: {event.data}")

# Main application
async def main():
    # Initialize processor
    processor = DataProcessor()

    # Register event handlers
    processor.emitter.on("cache_hit")(handle_cache_hit)
    processor.emitter.on("process_complete")(handle_process_complete)

    # Process some data
    data_items = ["hello", "world", "hello", "mtaio"]
    for data in data_items:
        result = await processor.process_data(data)
        print(f"Result for '{data}': {result}")

# Run the application
if __name__ == "__main__":
    asyncio.run(main())
```

This example demonstrates:

1. Event handling using `EventEmitter`
2. Caching with `TTLCache`
3. Task execution with `TaskExecutor`
4. Proper async/await usage

## Next Steps

Once you're comfortable with the basics, you can:

1. Learn more about [mtaio's core features](../api/core.md)
2. Explore [advanced usage patterns](advanced-usage.md)
3. Check out the [API reference](../api/index.md)
4. See more [examples in our repository](https://github.com/t3tra-dev/mtaio/tree/main/examples)

## Common Patterns

Here are some common patterns you'll use in mtaio applications:

### Resource Management

```python
from mtaio.resources import RateLimiter

limiter = RateLimiter(10.0)  # 10 operations per second

@limiter.limit
async def rate_limited_operation():
    # Your code here
    pass
```

### Event-Driven Architecture

```python
from mtaio.events import EventEmitter

emitter = EventEmitter()

@emitter.on("event_name")
async def handle_event(event):
    # Handle event
    pass

# Emit events
await emitter.emit("event_name", data)
```

### Caching Strategies

```python
from mtaio.cache import TTLCache
from mtaio.decorators import with_cache

cache = TTLCache[str](default_ttl=300.0)  # 5 minutes

@with_cache(cache)
async def cached_operation(key: str) -> str:
    # Expensive operation
    return result
```

## Best Practices

1. **Type Hints**: Always use type hints for better code quality and IDE support:
   ```python
   from mtaio.typing import AsyncFunc
   
   async def process_data(data: str) -> str:
       # Processing
       return result
   ```

2. **Resource Cleanup**: Use async context managers for proper resource cleanup:
   ```python
   async with TaskExecutor() as executor:
       # Work with executor
       pass  # Resources are automatically cleaned up
   ```

3. **Error Handling**: Use mtaio's exception hierarchy for proper error handling:
   ```python
   from mtaio.exceptions import MTAIOError
   
   try:
       await operation()
   except MTAIOError as e:
       # Handle mtaio-specific errors
       pass
   ```

4. **Configuration**: Keep configuration separate and use environment variables:
   ```python
   import os
   from mtaio.cache import TTLCache
   
   cache = TTLCache[str](
       default_ttl=float(os.getenv('CACHE_TTL', '300')),
       max_size=int(os.getenv('CACHE_SIZE', '1000'))
   )
   ```

## Getting Help

If you encounter any issues:

1. Check the [Troubleshooting](troubleshooting.md) guide
2. Search for similar issues in our [GitHub repository](https://github.com/t3tra-dev/mtaio/issues)
3. Create a new issue if your problem hasn't been addressed

Next, proceed to [Basic Usage](basic-usage.md) for more detailed information about mtaio's features.
