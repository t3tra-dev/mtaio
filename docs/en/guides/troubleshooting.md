# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with mtaio applications.

## Common Issues

### Resource Management

#### High Memory Usage

**Problem**: Application memory usage grows continuously.

**Possible Causes**:

- Unclosed resources
- Cache size not properly configured
- Memory leaks in event handlers

**Solutions**:

```python
from mtaio.resources import ResourceManager
from mtaio.cache import TTLCache

# Proper resource cleanup
async with ResourceManager() as manager:
    # Resources are automatically cleaned up
    pass

# Configure cache with appropriate size
cache = TTLCache[str](
    max_size=1000,  # Limit cache size
    default_ttl=300.0  # Clear items after 5 minutes
)

# Clean up event handlers
emitter = EventEmitter()
@emitter.on("event")
async def handler(event):
    # Process event
    pass

# Remove handler when no longer needed
emitter.remove_listener("event", handler)
```

#### Task Execution Timeouts

**Problem**: Tasks frequently timeout or take too long to execute.

**Solutions**:

```python
from mtaio.core import TaskExecutor
from mtaio.resources import TimeoutManager

# Configure appropriate timeouts
async with TimeoutManager(default_timeout=30.0) as tm:
    async with TaskExecutor() as executor:
        # Set concurrency limits
        result = await executor.gather(
            *tasks,
            limit=5  # Limit concurrent tasks
        )
```

### Event Handling

#### Event Handler Memory Leaks

**Problem**: Memory usage increases with event handler registration.

**Solution**:

```python
from mtaio.events import EventEmitter
import weakref

class EventHandlers:
    def __init__(self):
        self._handlers = weakref.WeakSet()
        self.emitter = EventEmitter()
    
    def register(self, handler):
        self._handlers.add(handler)
        self.emitter.on("event")(handler)
    
    def cleanup(self):
        self._handlers.clear()
```

#### Missing Event Handlers

**Problem**: Events are not being processed.

**Solution**:

```python
from mtaio.events import EventEmitter

async def setup_handlers():
    emitter = EventEmitter()
    
    # Add error handling
    @emitter.on("error")
    async def handle_error(event):
        print(f"Error occurred: {event.data}")
    
    # Verify handler registration
    if emitter.listener_count("error") == 0:
        raise RuntimeError("Error handler not registered")
```

### Cache Issues

#### Cache Inconsistency

**Problem**: Cache data becomes inconsistent across different parts of the application.

**Solution**:

```python
from mtaio.cache import DistributedCache
from mtaio.events import EventEmitter

async def setup_cache():
    cache = DistributedCache[str]([
        ("localhost", 5000),
        ("localhost", 5001)
    ])
    emitter = EventEmitter()
    
    @emitter.on("data_changed")
    async def invalidate_cache(event):
        affected_keys = event.data.get("keys", [])
        for key in affected_keys:
            await cache.delete(key)
```

#### Cache Performance Issues

**Problem**: Cache operations are slow or inefficient.

**Solution**:

```python
from mtaio.cache import TTLCache
from mtaio.monitoring import ResourceMonitor

async def optimize_cache():
    # Monitor cache performance
    monitor = ResourceMonitor()
    cache = TTLCache[str](
        default_ttl=60.0,  # Short TTL for frequently changing data
        max_size=1000
    )
    
    # Add cache metrics
    @monitor.on_metric("cache_hits")
    async def track_cache_hits(value):
        if value < 0.5:  # Less than 50% hit rate
            print("Cache hit rate is low, consider adjusting TTL")
```

## Debugging Tools

### Logging Setup

Configure detailed logging for debugging:

```python
import logging
from mtaio.logging import AsyncFileHandler

async def setup_debug_logging():
    logger = logging.getLogger("mtaio")
    logger.setLevel(logging.DEBUG)
    
    handler = AsyncFileHandler("debug.log")
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
```

### Performance Profiling

Profile your application to identify bottlenecks:

```python
from mtaio.monitoring import Profiler

async def profile_application():
    profiler = Profiler()
    
    @profiler.trace
    async def monitored_function():
        # Function to monitor
        pass
    
    # Get performance metrics
    profile = await profiler.get_profile()
    print(f"Execution time: {profile.total_time:.2f}s")
    print(f"Memory usage: {profile.memory_usage} MB")
```

## Error Messages

### Common Error Messages and Solutions

1. **`MTAIOError: Resource limit exceeded`**
    - Cause: Too many concurrent operations
    - Solution: Adjust resource limits or add rate limiting

2. **`TimeoutError: Operation timed out`**
    - Cause: Operation took too long to complete
    - Solution: Increase timeout or optimize operation

3. **`CacheError: Cache connection failed`**
    - Cause: Cannot connect to cache server
    - Solution: Check cache server status and configuration

4. **`EventError: Event handler failed`**
    - Cause: Exception in event handler
    - Solution: Add error handling to event handlers

## Best Practices

### Error Handling

Implement comprehensive error handling:

```python
from mtaio.exceptions import MTAIOError

async def handle_errors():
    try:
        # Your code here
        pass
    except MTAIOError as e:
        # Handle mtaio-specific errors
        logger.error(f"mtaio error: {e}")
    except Exception as e:
        # Handle unexpected errors
        logger.exception("Unexpected error occurred")
```

### Resource Cleanup

Ensure proper resource cleanup:

```python
from contextlib import AsyncExitStack

async def cleanup_resources():
    async with AsyncExitStack() as stack:
        # Add resources to stack
        executor = await stack.enter_async_context(TaskExecutor())
        cache = await stack.enter_async_context(TTLCache[str]())
        
        # Resources are automatically cleaned up
```

## Getting Help

If you continue to experience issues:

1. Check the [API documentation](../api/index.md) for correct usage
2. Search existing [GitHub issues](https://github.com/t3tra-dev/mtaio/issues)
3. Ask in [Community Discussions](https://github.com/t3tra-dev/mtaio/discussions)

When reporting issues, include:

- Python version
- mtaio version
- Minimal reproducible example
- Error messages and stack traces
- Relevant configuration settings
