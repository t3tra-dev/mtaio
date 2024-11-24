"""
Resource limiter implementation.

This module provides components for resource limiting:

* RateLimiter: Rate limiting implementation
* ConcurrencyLimiter: Concurrency limiting
* ResourceLimiter: General resource limiting
* TokenBucket: Token bucket algorithm
"""

from typing import (
    AsyncIterator,
    List,
    Optional,
    Any,
    Callable,
    Awaitable,
    TypeVar,
    Union,
)
from dataclasses import dataclass, field
import asyncio
import time
import logging
from contextlib import asynccontextmanager
from ..exceptions import ResourceLimitError

T = TypeVar("T")
logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """
    Token bucket implementation.

    :param rate: Token refill rate per second
    :type rate: float
    :param capacity: Maximum number of tokens
    :type capacity: int
    """

    rate: float
    capacity: int
    tokens: float = 0.0
    last_update: float = field(default_factory=time.monotonic)

    def __init__(self, rate: float, capacity: int):
        """Initialize bucket."""
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.monotonic()

    def update(self) -> None:
        """Update token count."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(
            self.capacity,
            self.tokens + (elapsed * self.rate)
        )
        self.last_update = now

    def consume(self, count: int = 1) -> bool:
        """
        Try to consume tokens.

        :param count: Number of tokens to consume
        :type count: int
        :return: True if tokens were consumed
        :rtype: bool
        """
        self.update()
        if self.tokens >= count:
            self.tokens -= count
            return True
        return False


class RateLimiter:
    """
    Rate limiter implementation.

    Example::

        limiter = RateLimiter(10.0)  # 10 requests per second

        @limiter.limit
        async def rate_limited_function():
            await process_request()
    """

    def __init__(self, rate: float, burst: Optional[int] = None):
        """
        Initialize rate limiter.

        :param rate: Maximum rate per window
        :type rate: float
        :param burst: Maximum burst size
        :type burst: Optional[int]
        """
        self.rate = float(rate)
        self.burst = int(burst or rate)
        self.bucket = TokenBucket(
            rate=self.rate,
            capacity=self.burst
        )
        self._lock = asyncio.Lock()
        self._waiters: List[asyncio.Future] = []

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens.

        :param tokens: Number of tokens to consume
        :raises ResourceLimitError: If rate limit is exceeded
        """
        async with self._lock:
            if not self.bucket.consume(tokens):
                raise ResourceLimitError(
                    f"Rate limit exceeded. Available tokens: {self.bucket.tokens:.2f}, "
                    f"Required: {tokens}, Burst limit: {self.burst}"
                )

    async def _release_waiters(self) -> None:
        """Release waiting tasks."""
        async with self._lock:
            for waiter in self._waiters[:]:
                if not waiter.done() and self.bucket.consume(1):
                    self._waiters.remove(waiter)
                    waiter.set_result(None)

    def limit(
        self, func: Optional[Callable[..., Awaitable[T]]] = None, *, tokens: int = 1
    ) -> Union[
        Callable[..., Awaitable[T]],
        Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]],
    ]:
        """
        Decorator for rate limiting.

        :param func: Function to decorate
        :type func: Optional[Callable[..., Awaitable[T]]]
        :param tokens: Number of tokens to consume
        :type tokens: int
        :return: Decorated function
        :rtype: Union[Callable[..., Awaitable[T]], Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]]
        """

        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                await self.acquire(tokens)
                try:
                    return await func(*args, **kwargs)
                finally:
                    await self._release_waiters()

            return wrapper

        if func is None:
            return decorator
        return decorator(func)


class ConcurrencyLimiter:
    """
    Concurrency limiter implementation.

    Example::

        limiter = ConcurrencyLimiter(5)  # Max 5 concurrent executions

        @limiter.limit
        async def concurrent_function():
            await process_task()
    """

    def __init__(self, limit: int):
        """
        Initialize concurrency limiter.

        :param limit: Maximum concurrent executions
        :type limit: int
        """
        if limit < 1:
            raise ValueError("Limit must be at least 1")
        self.semaphore = asyncio.Semaphore(limit)
        self.current = 0
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        """Acquire permission to proceed."""
        async with self.semaphore:
            async with self._lock:
                self.current += 1
            try:
                yield
            finally:
                async with self._lock:
                    self.current -= 1

    def limit(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """
        Decorator for concurrency limiting.

        :param func: Function to decorate
        :type func: Callable[..., Awaitable[T]]
        :return: Decorated function
        :rtype: Callable[..., Awaitable[T]]
        """

        async def wrapper(*args: Any, **kwargs: Any) -> T:
            async with self.acquire():
                return await func(*args, **kwargs)

        return wrapper


class ResourceLimiter:
    """
    Combined resource limiter implementation.

    Example::

        limiter = ResourceLimiter(
            rate=10.0,       # 10 requests per second
            concurrency=5,   # Max 5 concurrent executions
            window=1.0       # 1 second window
        )

        @limiter.limit
        async def limited_function():
            await process_request()
    """

    def __init__(
        self,
        rate: Optional[float] = None,
        concurrency: Optional[int] = None,
        window: float = 1.0,
    ):
        """
        Initialize resource limiter.

        :param rate: Maximum rate per window
        :type rate: Optional[float]
        :param concurrency: Maximum concurrent executions
        :type concurrency: Optional[int]
        :param window: Time window in seconds
        :type window: float
        """
        self.rate_limiter = (
            RateLimiter(rate, window=window) if rate is not None else None
        )
        self.concurrency_limiter = (
            ConcurrencyLimiter(concurrency) if concurrency is not None else None
        )

    def limit(
        self, func: Optional[Callable[..., Awaitable[T]]] = None, *, tokens: int = 1
    ) -> Union[
        Callable[..., Awaitable[T]],
        Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]],
    ]:
        """
        Decorator for resource limiting.

        :param func: Function to decorate
        :type func: Optional[Callable[..., Awaitable[T]]]
        :param tokens: Number of tokens to consume
        :type tokens: int
        :return: Decorated function
        :rtype: Union[Callable[..., Awaitable[T]], Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]]
        """

        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                # Apply rate limiting
                if self.rate_limiter:
                    await self.rate_limiter.acquire(tokens)

                # Apply concurrency limiting
                if self.concurrency_limiter:
                    async with self.concurrency_limiter.acquire():
                        result = await func(*args, **kwargs)
                else:
                    result = await func(*args, **kwargs)

                # Release rate limiter waiters
                if self.rate_limiter:
                    await self.rate_limiter._release_waiters()

                return result

            return wrapper

        if func is None:
            return decorator
        return decorator(func)


class BurstyRateLimiter(RateLimiter):
    """
    Rate limiter with burst support.

    Example::

        limiter = BurstyRateLimiter(
            rate=10.0,     # 10 requests per second
            burst=20       # Allow bursts up to 20 requests
        )
    """

    def __init__(self, rate: float, burst: int, initial_tokens: Optional[int] = None):
        """
        Initialize bursty rate limiter.

        :param rate: Token refill rate per second
        :type rate: float
        :param burst: Maximum burst size
        :type burst: int
        :param initial_tokens: Initial token count
        :type initial_tokens: Optional[int]
        """
        super().__init__(rate, burst)
        if initial_tokens is not None:
            self.bucket.tokens = min(initial_tokens, burst)

    async def wait_for_tokens(
        self, tokens: int = 1, timeout: Optional[float] = None
    ) -> bool:
        """
        Wait for tokens to become available.

        :param tokens: Number of tokens to wait for
        :type tokens: int
        :param timeout: Maximum wait time in seconds
        :type timeout: Optional[float]
        :return: True if tokens were acquired
        :rtype: bool
        """
        async with self._lock:
            if self.bucket.consume(tokens):
                return True

        if timeout is not None:
            try:
                async with asyncio.timeout(timeout):
                    await self.acquire(tokens)
                return True
            except asyncio.TimeoutError:
                return False
        else:
            await self.acquire(tokens)
            return True


class WindowedRateLimiter:
    """
    Rate limiter with sliding window.

    Example::

        limiter = WindowedRateLimiter(
            limit=100,      # Max 100 requests
            window=60.0     # Per 60 seconds
        )
    """

    def __init__(self, limit: int, window: float):
        """
        Initialize windowed rate limiter.

        :param limit: Maximum requests per window
        :type limit: int
        :param window: Window size in seconds
        :type window: float
        """
        self.limit = limit
        self.window = window
        self.timestamps: List[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire permission to proceed.

        :raises ResourceLimitError: If rate limit is exceeded
        """
        async with self._lock:
            now = time.monotonic()

            # Remove old timestamps
            cutoff = now - self.window
            while self.timestamps and self.timestamps[0] < cutoff:
                self.timestamps.pop(0)

            # Check if limit is exceeded
            if len(self.timestamps) >= self.limit:
                wait_time = self.timestamps[0] + self.window - now
                if wait_time > 0:
                    raise ResourceLimitError(
                        f"Rate limit exceeded. Try again in {wait_time:.2f} seconds"
                    )

            self.timestamps.append(now)

    def limit(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """
        Decorator for rate limiting.

        :param func: Function to decorate
        :type func: Callable[..., Awaitable[T]]
        :return: Decorated function
        :rtype: Callable[..., Awaitable[T]]
        """

        async def wrapper(*args: Any, **kwargs: Any) -> T:
            await self.acquire()
            return await func(*args, **kwargs)

        return wrapper
