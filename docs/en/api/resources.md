# Resources API Reference

The `mtaio.resources` module provides components for managing system resources, including rate limiting, timeouts, and concurrency control.

## RateLimiter

### Basic Usage

```python
from mtaio.resources import RateLimiter

# Create rate limiter
limiter = RateLimiter(10.0)  # 10 operations per second

# Use as decorator
@limiter.limit
async def rate_limited_operation():
    await perform_operation()

# Use with context manager
async def manual_rate_limit():
    async with limiter:
        await perform_operation()
```

### Class Reference

```python
class RateLimiter:
    def __init__(
        self,
        rate: float,
        burst: Optional[int] = None
    ):
        """
        Initialize rate limiter.

        Args:
            rate: Maximum operations per second
            burst: Maximum burst size (None for rate-based burst)
        """

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens from the rate limiter.

        Args:
            tokens: Number of tokens to acquire

        Raises:
            ResourceLimitError: If rate limit is exceeded
        """

    def limit(
        self,
        func: Optional[Callable[..., Awaitable[T]]] = None,
        *,
        tokens: int = 1
    ) -> Callable[..., Awaitable[T]]:
        """Decorator for rate limiting functions."""
```

## TimeoutManager

Provides timeout control for asynchronous operations.

### Basic Usage

```python
from mtaio.resources import TimeoutManager

async def operation_with_timeout():
    # Set timeout for a block of operations
    async with TimeoutManager(5.0) as tm:  # 5 seconds timeout
        result = await tm.run(long_running_operation())
        
        # Different timeout for specific operation
        result2 = await tm.run(
            another_operation(),
            timeout=2.0  # 2 seconds timeout
        )
```

### Class Reference

```python
class TimeoutManager:
    def __init__(self, default_timeout: Optional[float] = None):
        """
        Initialize timeout manager.

        Args:
            default_timeout: Default timeout in seconds
        """

    async def run(
        self,
        coro: Awaitable[T],
        *,
        timeout: Optional[float] = None
    ) -> T:
        """
        Run coroutine with timeout.

        Args:
            coro: Coroutine to execute
            timeout: Optional timeout override

        Returns:
            Result of the coroutine

        Raises:
            TimeoutError: If operation times out
        """
```

## ConcurrencyLimiter

Controls the number of concurrent operations.

### Basic Usage

```python
from mtaio.resources import ConcurrencyLimiter

# Create limiter with maximum 5 concurrent operations
limiter = ConcurrencyLimiter(5)

@limiter.limit
async def concurrent_operation():
    await process_task()

# Manual usage
async def manual_concurrency():
    async with limiter:
        await perform_operation()
```

### Class Reference

```python
class ConcurrencyLimiter:
    def __init__(self, limit: int):
        """
        Initialize concurrency limiter.

        Args:
            limit: Maximum number of concurrent operations
        """

    async def acquire(self) -> None:
        """
        Acquire permission to proceed.

        Raises:
            ResourceLimitError: If limit is exceeded
        """

    def limit(
        self,
        func: Callable[..., Awaitable[T]]
    ) -> Callable[..., Awaitable[T]]:
        """Decorator for limiting concurrency."""
```

## ResourceGroup

Manages multiple resources together.

### Basic Usage

```python
from mtaio.resources import ResourceGroup

async def manage_resources():
    group = ResourceGroup()
    
    # Add resources to group
    rate_limiter = await group.add(RateLimiter(10.0))
    timeout = await group.add(TimeoutManager(5.0))
    
    # Resources are automatically managed
    async with group:
        async with timeout:
            await rate_limiter.acquire()
            await perform_operation()
```

### Class Reference

```python
class ResourceGroup:
    async def add(self, resource: Any) -> Any:
        """
        Add resource to group.

        Args:
            resource: Resource to manage

        Returns:
            Added resource
        """

    async def remove(self, resource: Any) -> None:
        """
        Remove resource from group.

        Args:
            resource: Resource to remove
        """
```

## Advanced Features

### Adaptive Rate Limiting

```python
from mtaio.resources import RateLimiter
from typing import Dict

class AdaptiveRateLimiter(RateLimiter):
    def __init__(self):
        self.rates: Dict[str, float] = {}
        self._current_load = 0.0
    
    async def acquire(self, resource_id: str) -> None:
        rate = self.rates.get(resource_id, 1.0)
        if self._current_load > 0.8:  # 80% load
            rate *= 0.5  # Reduce rate
        await super().acquire(tokens=1/rate)
    
    def adjust_rate(self, resource_id: str, load: float) -> None:
        self._current_load = load
        if load > 0.9:  # High load
            self.rates[resource_id] *= 0.8
        elif load < 0.5:  # Low load
            self.rates[resource_id] *= 1.2
```

### Cascading Timeouts

```python
from mtaio.resources import TimeoutManager
from contextlib import asynccontextmanager

class TimeoutController:
    def __init__(self):
        self.timeouts = TimeoutManager()
    
    @asynccontextmanager
    async def cascading_timeout(self, timeouts: list[float]):
        """Implements cascading timeouts with fallback."""
        for timeout in timeouts:
            try:
                async with self.timeouts.timeout(timeout):
                    yield
                break
            except TimeoutError:
                if timeout == timeouts[-1]:
                    raise
                continue
```

## Best Practices

### Resource Cleanup

```python
from contextlib import AsyncExitStack

async def cleanup_resources():
    async with AsyncExitStack() as stack:
        # Add resources to stack
        rate_limiter = await stack.enter_async_context(RateLimiter(10.0))
        timeout = await stack.enter_async_context(TimeoutManager(5.0))
        
        # Resources are automatically cleaned up
```

### Error Handling

```python
from mtaio.exceptions import ResourceLimitError, TimeoutError

async def handle_resource_errors():
    try:
        async with TimeoutManager(5.0) as tm:
            await tm.run(operation())
    except TimeoutError:
        logger.error("Operation timed out")
    except ResourceLimitError as e:
        logger.error(f"Resource limit exceeded: {e}")
```

### Performance Optimization

1. **Rate Limiting Strategy**
   ```python
   # Balance between protection and performance
   rate_limiter = RateLimiter(
       rate=100.0,    # 100 operations per second
       burst=20       # Allow bursts of 20 operations
   )
   ```

2. **Timeout Configuration**
   ```python
   # Set appropriate timeouts
   timeout_manager = TimeoutManager(
       default_timeout=30.0  # Default 30 seconds
   )
   ```

3. **Concurrency Control**
   ```python
   # Limit concurrent operations based on system capacity
   concurrency_limiter = ConcurrencyLimiter(
       limit=cpu_count() * 2  # 2 operations per CPU core
   )
   ```

## Error Handling Examples

```python
from mtaio.exceptions import (
    ResourceError,
    ResourceLimitError,
    TimeoutError
)

async def handle_errors():
    try:
        async with RateLimiter(10.0) as limiter:
            await limiter.acquire()
            
    except ResourceLimitError:
        # Handle rate limit exceeded
        logger.warning("Rate limit exceeded")
        await asyncio.sleep(1)
        
    except TimeoutError:
        # Handle timeout
        logger.error("Operation timed out")
        
    except ResourceError as e:
        # Handle general resource errors
        logger.error(f"Resource error: {e}")
```

## Integration Examples

### Web Application

```python
from mtaio.resources import RateLimiter, TimeoutManager

class RateLimitedAPI:
    def __init__(self):
        self.rate_limiter = RateLimiter(100.0)  # 100 requests/second
        self.timeout = TimeoutManager(5.0)      # 5 second timeout
    
    async def handle_request(self, request):
        async with self.timeout:
            await self.rate_limiter.acquire()
            return await process_request(request)
```

### Task Processing

```python
from mtaio.resources import ConcurrencyLimiter

class TaskProcessor:
    def __init__(self):
        self.limiter = ConcurrencyLimiter(10)  # 10 concurrent tasks
    
    async def process_tasks(self, tasks: list):
        async with self.limiter:
            results = []
            for task in tasks:
                result = await self.process_task(task)
                results.append(result)
            return results
```

## See Also

- [Core API Reference](core.md) for base functionality
- [Events API Reference](events.md) for event handling
- [Examples Repository](https://github.com/t3tra-dev/mtaio/tree/main/examples/resources.py)
