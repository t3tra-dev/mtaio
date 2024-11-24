# Typing API Reference

The `mtaio.typing` module provides type definitions and protocols used throughout the mtaio framework, enabling better code completion and static type checking.

## Basic Types

### Generic Type Variables

```python
from mtaio.typing import T, T_co, T_contra, K, V

# Basic generic type variables
T = TypeVar("T")               # Invariant type variable
T_co = TypeVar("T_co", covariant=True)       # Covariant type variable
T_contra = TypeVar("T_contra", contravariant=True)  # Contravariant type variable
K = TypeVar("K")               # Key type variable
V = TypeVar("V")               # Value type variable
```

### Common Type Aliases

```python
from mtaio.typing import (
    JSON,
    PathLike,
    TimeValue,
    Primitive
)

# JSON-compatible types
JSON = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

# Path-like types
PathLike = Union[str, Path]

# Time value types
TimeValue = Union[int, float, timedelta]

# Primitive types
Primitive = Union[str, int, float, bool, None]
```

## Function Types

### Callback Types

```python
from mtaio.typing import (
    Callback,
    AsyncCallback,
    ErrorCallback,
    AsyncErrorCallback
)

# Synchronous and asynchronous callbacks
Callback = Callable[..., Any]
AsyncCallback = Callable[..., Awaitable[Any]]

# Error handling callbacks
ErrorCallback = Callable[[Exception], Any]
AsyncErrorCallback = Callable[[Exception], Awaitable[Any]]

# Cleanup callbacks
CleanupCallback = Callable[[], Any]
AsyncCleanupCallback = Callable[[], Awaitable[Any]]
```

### Function Type Definitions

```python
from mtaio.typing import (
    SyncFunc,
    AsyncFunc,
    AsyncCallable,
    CoroFunc,
    AnyFunc,
    Decorator
)

# Function types
SyncFunc = Callable[..., T]
AsyncFunc = Callable[..., Awaitable[T]]
AsyncCallable = Callable[..., Awaitable[T]]
CoroFunc = TypeVar('CoroFunc', bound=AsyncCallable[Any])

# Combined function types
AnyFunc = Union[SyncFunc[T], AsyncFunc[T]]

# Decorator type
Decorator = Callable[[AnyFunc[T]], AnyFunc[T]]
```

## Protocol Definitions

### Resource Management

```python
from mtaio.typing import Resource, ResourceManager

@runtime_checkable
class Resource(Protocol):
    """Protocol for resource objects."""
    
    async def acquire(self) -> None:
        """Acquire resource."""
        ...

    async def release(self) -> None:
        """Release resource."""
        ...

class ResourceManager(AsyncContextManager[Resource], Protocol):
    """Protocol for resource managers."""
    
    async def __aenter__(self) -> Resource:
        """Enter context and acquire resource."""
        ...

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> Optional[bool]:
        """Exit context and release resource."""
        ...
```

### Event Handling

```python
from mtaio.typing import Event, EventHandler

@runtime_checkable
class Event(Protocol[T]):
    """Protocol for event objects."""
    
    @property
    def name(self) -> str:
        """Event name."""
        ...

    @property
    def data(self) -> T:
        """Event data."""
        ...

class EventHandler(Protocol[T]):
    """Protocol for event handlers."""
    
    async def handle(self, event: Event[T]) -> None:
        """Handle event."""
        ...
```

### Cache Types

```python
from mtaio.typing import CacheKey, CacheValue

@runtime_checkable
class CacheKey(Protocol):
    """Protocol for cache keys."""
    
    def __str__(self) -> str:
        """Convert to string."""
        ...

    def __hash__(self) -> int:
        """Get hash value."""
        ...

class CacheValue(Protocol):
    """Protocol for cache values."""
    
    async def serialize(self) -> bytes:
        """Serialize value."""
        ...

    @classmethod
    async def deserialize(cls, data: bytes) -> Any:
        """Deserialize value."""
        ...
```

## Utility Types

### Result Type

```python
from mtaio.typing import Result

class Result(Generic[T]):
    """Container for operation results."""

    def __init__(
        self,
        value: Optional[T] = None,
        error: Optional[Exception] = None
    ) -> None:
        self.value = value
        self.error = error
        self.success = error is None

    def unwrap(self) -> T:
        """
        Get value or raise error.

        Returns:
            The contained value

        Raises:
            The contained error if present
        """
        if self.error:
            raise self.error
        if self.value is None:
            raise ValueError("Result has no value")
        return self.value
```

### Configuration Types

```python
from mtaio.typing import ConfigProtocol, Config

@runtime_checkable
class ConfigProtocol(Protocol):
    """Protocol for configuration objects."""

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        ...

    def get_path(self, key: str, default: Optional[PathLike] = None) -> PathLike:
        """Get path value."""
        ...

    def get_timedelta(self, key: str, default: Optional[TimeValue] = None) -> timedelta:
        """Get timedelta value."""
        ...

class Config(Dict[str, Any], ConfigProtocol):
    """Configuration implementation."""
    pass
```

### Factory Types

```python
from mtaio.typing import Factory, AsyncFactory

class Factory(Protocol[T]):
    """Protocol for factory objects."""
    
    def create(self) -> T:
        """Create new instance."""
        ...

class AsyncFactory(Protocol[T]):
    """Protocol for async factory objects."""
    
    async def create(self) -> T:
        """Create new instance asynchronously."""
        ...
```

## Best Practices

### Using Type Hints

```python
from mtaio.typing import AsyncFunc, Result

# Function type hints
async def process_data(func: AsyncFunc[str]) -> Result[str]:
    try:
        result = await func()
        return Result(value=result)
    except Exception as e:
        return Result(error=e)

# Protocol usage
class DataProcessor(AsyncFactory[str]):
    async def create(self) -> str:
        return await self.process()

    async def process(self) -> str:
        # Processing implementation
        return "processed data"
```

### Generic Type Usage

```python
from mtaio.typing import T, CacheValue

class CustomCache(Generic[T]):
    async def get(self, key: str) -> Optional[T]:
        ...

    async def set(self, key: str, value: T) -> None:
        ...

# Implementation with specific type
cache = CustomCache[str]()
```

### Protocol Inheritance

```python
from mtaio.typing import Resource, EventHandler

class ManagedResource(Resource, EventHandler[str]):
    async def acquire(self) -> None:
        ...

    async def release(self) -> None:
        ...

    async def handle(self, event: Event[str]) -> None:
        ...
```

## Error Handling

```python
from mtaio.typing import Result, AsyncFunc

async def safe_operation(func: AsyncFunc[T]) -> Result[T]:
    try:
        result = await func()
        return Result(value=result)
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return Result(error=e)

# Usage
result = await safe_operation(async_function)
if result.success:
    value = result.unwrap()
else:
    handle_error(result.error)
```

## Integration Examples

### Resource Management

```python
from mtaio.typing import Resource, ResourceManager

class DatabaseConnection(Resource):
    async def acquire(self) -> None:
        await self.connect()

    async def release(self) -> None:
        await self.disconnect()

class ConnectionManager(ResourceManager[DatabaseConnection]):
    async def __aenter__(self) -> DatabaseConnection:
        conn = DatabaseConnection()
        await conn.acquire()
        return conn

    async def __aexit__(self, *args) -> None:
        await self.resource.release()
```

### Event System

```python
from mtaio.typing import Event, EventHandler

class DataEvent(Event[Dict[str, Any]]):
    def __init__(self, name: str, data: Dict[str, Any]):
        self._name = name
        self._data = data

    @property
    def name(self) -> str:
        return self._name

    @property
    def data(self) -> Dict[str, Any]:
        return self._data

class DataHandler(EventHandler[Dict[str, Any]]):
    async def handle(self, event: Event[Dict[str, Any]]) -> None:
        await self.process_data(event.data)
```

## See Also

- [Core API Reference](core.md) for base functionality
- [Exceptions API Reference](exceptions.md) for error handling
- [Examples Repository](https://github.com/t3tra-dev/mtaio/tree/main/examples/typing.py)
