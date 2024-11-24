# Decorators API Reference

The `mtaio.decorators` module provides utility decorators for enhancing async functions with additional functionality such as caching, retries, rate limiting, and more.

## Adapters

Decorators for adapting between different async patterns.

### async_adapter

Converts synchronous functions to asynchronous functions.

```python
from mtaio.decorators import async_adapter

# Basic usage
@async_adapter
def cpu_intensive(data: str) -> str:
    # CPU-intensive operation
    return processed_data

# With custom executor
@async_adapter(executor=ThreadPoolExecutor(max_workers=4))
def parallel_operation(data: str) -> str:
    return processed_data

# Using the decorated function
async def main():
    result = await cpu_intensive("data")
```

### async_iterator

Converts synchronous iterables to async iterators.

```python
from mtaio.decorators import async_iterator

@async_iterator(chunk_size=10)
def generate_data() -> Iterable[int]:
    return range(1000)

async def process_data():
    async for items in generate_data():
        # Process chunk of items
        pass
```

### async_context_adapter

Converts synchronous context managers to async context managers.

```python
from mtaio.decorators import async_context_adapter
from contextlib import contextmanager

@async_context_adapter
@contextmanager
def resource_manager():
    resource = acquire_resource()
    try:
        yield resource
    finally:
        release_resource(resource)

async def use_resource():
    async with resource_manager() as resource:
        await process(resource)
```

## Control Flow

Decorators for controlling function execution.

### with_timeout

Adds timeout control to async functions.

```python
from mtaio.decorators import with_timeout

@with_timeout(5.0)  # 5 seconds timeout
async def api_call() -> dict:
    return await make_request()

# With custom error message
@with_timeout(10.0, error_message="API call timed out")
async def long_operation() -> None:
    await process_data()
```

### with_retry

Adds retry logic for failed operations.

```python
from mtaio.decorators import with_retry

# Basic retry
@with_retry(max_attempts=3)
async def unstable_operation() -> str:
    return await flaky_service_call()

# Advanced retry configuration
@with_retry(
    max_attempts=5,
    delay=1.0,
    backoff_factor=2.0,
    exceptions=(ConnectionError, TimeoutError)
)
async def network_operation() -> bytes:
    return await fetch_data()
```

### with_rate_limit

Adds rate limiting to function calls.

```python
from mtaio.decorators import with_rate_limit

@with_rate_limit(10.0)  # 10 calls per second
async def rate_limited_api() -> dict:
    return await api_call()

# With burst allowance
@with_rate_limit(rate=5.0, burst=10)
async def burst_allowed_operation() -> None:
    await process()
```

### with_circuit_breaker

Implements the circuit breaker pattern.

```python
from mtaio.decorators import with_circuit_breaker

@with_circuit_breaker(
    failure_threshold=5,    # Open after 5 failures
    reset_timeout=60.0,     # Try to reset after 60 seconds
    half_open_timeout=5.0   # Allow one test call after timeout
)
async def protected_operation() -> str:
    return await external_service_call()
```

### with_fallback

Provides fallback behavior for failed operations.

```python
from mtaio.decorators import with_fallback

# With static fallback
@with_fallback("default_value")
async def get_data() -> str:
    return await fetch_data()

# With fallback function
@with_fallback(lambda: get_cached_data())
async def fetch_user(user_id: str) -> dict:
    return await db_query(user_id)
```

### with_cache

Adds caching to function results.

```python
from mtaio.decorators import with_cache
from mtaio.cache import TTLCache

cache = TTLCache[str]()

@with_cache(cache)
async def expensive_calculation(input: str) -> str:
    return await compute_result(input)

# With custom key function
@with_cache(cache, key_func=lambda x, y: f"{x}:{y}")
async def parameterized_operation(x: int, y: int) -> int:
    return await compute(x, y)
```

## Advanced Usage

### Combining Decorators

Decorators can be combined to add multiple behaviors:

```python
@with_timeout(5.0)
@with_retry(max_attempts=3)
@with_cache(cache)
async def robust_operation() -> dict:
    return await fetch_data()
```

### Custom Adapters

Creating custom adapters:

```python
from mtaio.decorators import CallbackAdapter

class CustomAdapter:
    def __init__(self, timeout: float = 30.0):
        self.adapter = CallbackAdapter[str](timeout)
    
    def callback(self, result: str) -> None:
        self.adapter.callback(result)
    
    async def wait(self) -> str:
        return await self.adapter.wait()
```

### Error Handling

Handling decorator-specific errors:

```python
from mtaio.exceptions import (
    TimeoutError,
    RetryError,
    RateLimitError,
    CircuitBreakerError
)

async def handle_errors():
    try:
        await protected_operation()
    except TimeoutError:
        # Handle timeout
        pass
    except RetryError as e:
        # Handle retry exhaustion
        print(f"Failed after {e.attempts} attempts")
    except RateLimitError as e:
        # Handle rate limit
        print(f"Rate limit exceeded: {e.limit}")
```

## Best Practices

1. **Order of Decorators**
   ```python
   # Timeout should be outermost to properly control execution time
   @with_timeout(5.0)
   @with_retry(max_attempts=3)
   @with_cache(cache)
   async def optimized_operation():
       pass
   ```

2. **Resource Cleanup**
   ```python
   # Use async context managers for proper cleanup
   @async_context_adapter
   @contextmanager
   def managed_resource():
       try:
           yield setup_resource()
       finally:
           cleanup_resource()
   ```

3. **Error Handling**
   ```python
   # Handle specific exceptions for better error control
   @with_fallback(
       fallback=default_value,
       exceptions=(ConnectionError, TimeoutError)
   )
   async def safe_operation():
       pass
   ```

## Performance Considerations

1. **Caching Strategy**
   ```python
   # Use appropriate cache settings
   @with_cache(
       TTLCache[str](
           default_ttl=300.0,  # 5 minutes
           max_size=1000
       )
   )
   async def cached_operation():
       pass
   ```

2. **Rate Limiting**
   ```python
   # Balance between protection and performance
   @with_rate_limit(
       rate=100.0,    # 100 calls per second
       burst=20       # Allow bursts
   )
   async def high_throughput_operation():
       pass
   ```

3. **Retry Timing**
   ```python
   # Use exponential backoff for retries
   @with_retry(
       delay=1.0,
       backoff_factor=2.0  # 1s, 2s, 4s, 8s...
   )
   async def network_operation():
       pass
   ```

## See Also

- [Core API Reference](core.md) for base functionality
- [Cache API Reference](cache.md) for caching operations
- [Resources API Reference](resources.md) for resource management
- [Examples Repository](https://github.com/t3tra-dev/mtaio/tree/main/examples/decorators.py)
