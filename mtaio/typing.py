"""
mtaio type definitions.

This module defines custom types and protocols used throughout the mtaio framework.
It provides type hints for better code completion and static type checking.
"""

from typing import (
    Callable,
    TypeVar,
    Generic,
    Protocol,
    Union,
    Any,
    Awaitable,
    AsyncIterator,
    Dict,
    List,
    Optional,
    runtime_checkable,
    Type,
    AsyncContextManager,
)
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# Generic type variables
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)
K = TypeVar("K")
V = TypeVar("V")

# Basic type aliases
JSON = Union[Dict[str, Any], List[Any], str, int, float, bool, None]
PathLike = Union[str, Path]
TimeValue = Union[int, float, timedelta]
Primitive = Union[str, int, float, bool, None]

# Callback type definitions
Callback = Callable[..., Any]
AsyncCallback = Callable[..., Awaitable[Any]]
ErrorCallback = Callable[[Exception], Any]
AsyncErrorCallback = Callable[[Exception], Awaitable[Any]]
CleanupCallback = Callable[[], Any]
AsyncCleanupCallback = Callable[[], Awaitable[Any]]

# Function type definitions
SyncFunc = Callable[..., T]
AsyncFunc = Callable[..., Awaitable[T]]
AsyncCallable = Callable[..., Awaitable[T]]
CoroFunc = TypeVar('CoroFunc', bound=AsyncCallable[Any])
AnyFunc = Union[SyncFunc[T], AsyncFunc[T]]
Decorator = Callable[[AnyFunc[T]], AnyFunc[T]]


@runtime_checkable
class SupportsAsyncClose(Protocol):
    """Protocol for objects that can be closed asynchronously."""

    async def close(self) -> None:
        """Close the object asynchronously."""
        ...


@runtime_checkable
class SupportsAsyncRead(Protocol):
    """Protocol for objects that can be read asynchronously."""

    async def read(self, size: int = -1) -> bytes:
        """Read data asynchronously."""
        ...


@runtime_checkable
class SupportsAsyncWrite(Protocol):
    """Protocol for objects that can be written asynchronously."""

    async def write(self, data: bytes) -> None:
        """Write data asynchronously."""
        ...


@runtime_checkable
class SupportsAsyncReadWrite(SupportsAsyncRead, SupportsAsyncWrite, Protocol):
    """Protocol for objects that support both async read and write."""

    pass


@runtime_checkable
class SupportsAsyncIter(Protocol[T_co]):
    """Protocol for objects that support async iteration."""

    def __aiter__(self) -> AsyncIterator[T_co]:
        """Return async iterator."""
        ...


@runtime_checkable
class SupportsAsyncSerialize(Protocol):
    """Protocol for objects that can be serialized asynchronously."""

    async def serialize(self) -> bytes:
        """Serialize object to bytes."""
        ...

    @classmethod
    async def deserialize(cls, data: bytes) -> Any:
        """Deserialize object from bytes."""
        ...


@runtime_checkable
class SupportsAsyncValidate(Protocol):
    """Protocol for objects that can be validated asynchronously."""

    async def validate(self) -> bool:
        """Validate object state."""
        ...

    async def validate_field(self, field: str) -> bool:
        """Validate specific field."""
        ...


@runtime_checkable
class SupportsAsyncHash(Protocol):
    """Protocol for objects that can be hashed asynchronously."""

    async def hash(self) -> bytes:
        """Generate hash of object."""
        ...


@runtime_checkable
class SupportsAsyncCompare(Protocol):
    """Protocol for objects that can be compared asynchronously."""

    async def equals(self, other: Any) -> bool:
        """Compare with another object."""
        ...

    async def compare(self, other: Any) -> int:
        """Compare and return ordering (-1, 0, 1)."""
        ...


class AsyncContextDecorator:
    """Base class for async context manager decorators."""

    def __call__(self, func: AnyFunc[T]) -> AnyFunc[T]:
        """Decorate function with async context."""
        if asyncio.iscoroutinefunction(func):

            async def wrapper(*args: Any, **kwargs: Any) -> T:
                async with self:
                    return await func(*args, **kwargs)

            return wrapper
        else:

            def wrapper(*args: Any, **kwargs: Any) -> T:
                async def _wrapped() -> T:
                    async with self:
                        return func(*args, **kwargs)

                return asyncio.run(_wrapped())

            return wrapper


class AsyncIteratorWrapper(AsyncIterator[T]):
    """Wrapper to convert sync iterator to async iterator."""

    def __init__(self, iterator: Any) -> None:
        """Initialize wrapper."""
        self.iterator = iterator

    def __aiter__(self) -> AsyncIterator[T]:
        """Return self as async iterator."""
        return self

    async def __anext__(self) -> T:
        """Get next item asynchronously."""
        try:
            return next(self.iterator)
        except StopIteration:
            raise StopAsyncIteration


# Resource management types
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


# Event types
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


# Cache types
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


# Message types
class Message(Protocol[T]):
    """Protocol for message objects."""

    @property
    def id(self) -> str:
        """Message ID."""
        ...

    @property
    def payload(self) -> T:
        """Message payload."""
        ...

    @property
    def timestamp(self) -> datetime:
        """Message timestamp."""
        ...


class MessageHandler(Protocol[T]):
    """Protocol for message handlers."""

    async def handle(self, message: Message[T]) -> None:
        """Handle message."""
        ...


# Task types
class Task(Protocol[T]):
    """Protocol for task objects."""

    @property
    def id(self) -> str:
        """Task ID."""
        ...

    async def run(self) -> T:
        """Run task."""
        ...

    async def cancel(self) -> None:
        """Cancel task."""
        ...


class TaskExecutor(Protocol[T]):
    """Protocol for task executors."""

    async def execute(self, task: Task[T]) -> T:
        """Execute task."""
        ...


# Result types
class Result(Generic[T]):
    """Container for operation results."""

    def __init__(
        self, value: Optional[T] = None, error: Optional[Exception] = None
    ) -> None:
        """Initialize result."""
        self.value = value
        self.error = error
        self.success = error is None

    def unwrap(self) -> T:
        """Get value or raise error."""
        if self.error:
            raise self.error
        if self.value is None:
            raise ValueError("Result has no value")
        return self.value

    def __repr__(self) -> str:
        """Get string representation."""
        if self.success:
            return f"Result(value={self.value!r})"
        return f"Result(error={self.error!r})"


# Utility types
class Closeable(Protocol):
    """Protocol for closeable objects."""

    def close(self) -> None:
        """Close object."""
        ...


class AsyncCloseable(Protocol):
    """Protocol for async closeable objects."""

    async def close(self) -> None:
        """Close object asynchronously."""
        ...


class Disposable(Protocol):
    """Protocol for disposable objects."""

    def dispose(self) -> None:
        """Dispose object."""
        ...


class AsyncDisposable(Protocol):
    """Protocol for async disposable objects."""

    async def dispose(self) -> None:
        """Dispose object asynchronously."""
        ...


# Configuration types
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


class Config(Dict[str, Any]):
    """Configuration implementation."""

    def get_path(self, key: str, default: Optional[PathLike] = None) -> PathLike:
        """Get path value."""
        value = self.get(key, default)
        if value is None:
            raise ValueError(f"Missing path configuration: {key}")
        return Path(value)

    def get_timedelta(self, key: str, default: Optional[TimeValue] = None) -> timedelta:
        """Get timedelta value."""
        value = self.get(key, default)
        if value is None:
            raise ValueError(f"Missing timedelta configuration: {key}")
        if isinstance(value, timedelta):
            return value
        if isinstance(value, (int, float)):
            return timedelta(seconds=value)
        raise ValueError(f"Invalid timedelta value for {key}: {value}")


# Factory types
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


# Builder types
class Builder(Protocol[T]):
    """Protocol for builder objects."""

    def build(self) -> T:
        """Build instance."""
        ...


class AsyncBuilder(Protocol[T]):
    """Protocol for async builder objects."""

    async def build(self) -> T:
        """Build instance asynchronously."""
        ...
