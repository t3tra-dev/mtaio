# Exceptions API Reference

The `mtaio.exceptions` module provides a comprehensive exception hierarchy for error handling in mtaio applications.

## Exception Hierarchy

### Base Exception

```python
class MTAIOError(Exception):
    """Base exception for all mtaio errors."""
    def __init__(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.message = message
        super().__init__(message, *args)
```

All mtaio exceptions inherit from this base class.

## Core Exceptions

### ExecutionError

Raised when task execution fails.

```python
from mtaio.exceptions import ExecutionError

try:
    async with TaskExecutor() as executor:
        await executor.run(task)
except ExecutionError as e:
    print(f"Task execution failed: {e}")
```

### TimeoutError

Raised when an operation times out.

```python
from mtaio.exceptions import TimeoutError

try:
    async with TimeoutManager(5.0):
        await long_running_operation()
except TimeoutError as e:
    print(f"Operation timed out: {e}")
```

### RetryError

Raised when retry attempts are exhausted.

```python
class RetryError(MTAIOError):
    def __init__(
        self,
        message: str,
        attempts: Optional[int] = None,
        last_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error

# Usage example
try:
    @with_retry(max_attempts=3)
    async def unstable_operation():
        pass
except RetryError as e:
    print(f"Failed after {e.attempts} attempts")
    if e.last_error:
        print(f"Last error: {e.last_error}")
```

## Resource Management Exceptions

### ResourceLimitError

Raised when resource limits are exceeded.

```python
from mtaio.exceptions import ResourceLimitError

try:
    limiter = RateLimiter(10.0)  # 10 ops/second
    await limiter.acquire()
except ResourceLimitError as e:
    print(f"Rate limit exceeded: {e}")
```

### ResourceLockError

Raised when resource lock operations fail.

```python
from mtaio.exceptions import ResourceLockError

try:
    async with resource_lock:
        await process_resource()
except ResourceLockError as e:
    print(f"Failed to acquire lock: {e}")
```

## Cache Exceptions

### CacheError

Base exception for cache operations.

```python
class CacheError(MTAIOError):
    """Base exception for cache-related errors."""
    pass

class CacheKeyError(CacheError):
    """Raised when a cache key is invalid or not found."""
    pass

class CacheConnectionError(CacheError):
    """Raised when cache connection fails."""
    pass

# Usage example
try:
    await cache.get("key")
except CacheKeyError:
    print("Key not found")
except CacheConnectionError:
    print("Failed to connect to cache")
except CacheError as e:
    print(f"Cache operation failed: {e}")
```

## Event Exceptions

### EventError

Base exception for event operations.

```python
class EventError(MTAIOError):
    """Base exception for event-related errors."""
    pass

class EventEmitError(EventError):
    """Raised when event emission fails."""
    pass

class EventHandlerError(EventError):
    """Raised when event handler fails."""
    pass

# Usage example
try:
    await emitter.emit("event", data)
except EventEmitError:
    print("Failed to emit event")
except EventHandlerError:
    print("Event handler failed")
```

## Protocol Exceptions

### ProtocolError

Base exception for protocol operations.

```python
class ProtocolError(MTAIOError):
    """Base exception for protocol-related errors."""
    pass

class ASGIError(ProtocolError):
    """Raised when ASGI protocol error occurs."""
    pass

class MQTTError(ProtocolError):
    """Raised when MQTT protocol error occurs."""
    pass

# Usage example
try:
    await mqtt_client.connect()
except MQTTError as e:
    print(f"MQTT connection failed: {e}")
```

## Error Handling Best Practices

### Specific Exception Handling

Handle exceptions from most specific to most general:

```python
try:
    await operation()
except CacheKeyError:
    # Handle specific key error
    pass
except CacheError:
    # Handle general cache error
    pass
except MTAIOError:
    # Handle any mtaio error
    pass
except Exception:
    # Handle unexpected errors
    pass
```

### Custom Exception Classes

Creating custom exceptions:

```python
class CustomOperationError(MTAIOError):
    def __init__(
        self,
        message: str,
        operation_id: str,
        *args: Any
    ) -> None:
        super().__init__(message, *args)
        self.operation_id = operation_id

# Usage
try:
    raise CustomOperationError(
        "Operation failed",
        operation_id="123"
    )
except CustomOperationError as e:
    print(f"Operation {e.operation_id} failed: {e.message}")
```

### Exception Utility Functions

```python
from mtaio.exceptions import format_exception, wrap_exception

# Format exception with details
try:
    await operation()
except MTAIOError as e:
    error_message = format_exception(e)
    logger.error(error_message)

# Wrap exception with new type
try:
    await operation()
except ConnectionError as e:
    raise wrap_exception(
        e,
        CacheConnectionError,
        "Cache connection failed"
    )
```

### Async Context Manager Error Handling

```python
class SafeResource:
    async def __aenter__(self):
        try:
            await self.connect()
            return self
        except Exception as e:
            raise ResourceError("Failed to acquire resource") from e

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            await self.disconnect()
        except Exception as e:
            # Log but don't raise during cleanup
            logger.error(f"Cleanup error: {e}")
```

## Common Error Patterns

### Retry Pattern

```python
async def with_retry(
    operation: Callable,
    max_attempts: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (MTAIOError,)
):
    last_error = None
    for attempt in range(max_attempts):
        try:
            return await operation()
        except exceptions as e:
            last_error = e
            if attempt == max_attempts - 1:
                raise RetryError(
                    "Operation failed after retries",
                    attempts=attempt + 1,
                    last_error=last_error
                )
            await asyncio.sleep(2 ** attempt)
```

### Circuit Breaker Pattern

```python
class CircuitBreakerError(MTAIOError):
    def __init__(
        self,
        message: str,
        failures: Optional[int] = None,
        reset_timeout: Optional[float] = None
    ):
        super().__init__(message)
        self.failures = failures
        self.reset_timeout = reset_timeout

# Usage
breaker = CircuitBreaker(failure_threshold=5)
try:
    await breaker.call(operation)
except CircuitBreakerError as e:
    print(f"Circuit breaker open: {e.failures} failures")
```

## See Also

- [Core API Reference](core.md) for core functionality
- [Events API Reference](events.md) for event handling
- [Examples Repository](https://github.com/t3tra-dev/mtaio/tree/main/examples/error-handling.py)
