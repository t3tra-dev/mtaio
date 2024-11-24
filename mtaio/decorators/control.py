"""
Control decorators for async functions.

This module provides decorators for controlling async function execution:

* with_timeout: Add timeout control to async functions
* with_retry: Add retry logic to async functions
* with_rate_limit: Add rate limiting to async functions
* with_circuit_breaker: Add circuit breaker pattern
* with_fallback: Add fallback logic
* with_cache: Add caching
"""

from typing import (
    TypeVar,
    Callable,
    Awaitable,
    Optional,
    Union,
    Any,
    Type,
    Dict,
    List,
    Tuple,
    cast,
)
import asyncio
import functools
import time
import logging
from ..exceptions import (
    TimeoutError,
    RetryError,
    RateLimitError,
    CircuitBreakerError,
    FallbackError,
)

T = TypeVar("T")
logger = logging.getLogger(__name__)


def with_timeout(
    seconds: float, *, error_message: Optional[str] = None, cancel_task: bool = True
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Add timeout control to an async function.

    :param seconds: Timeout duration in seconds
    :type seconds: float
    :param error_message: Custom error message
    :type error_message: Optional[str]
    :param cancel_task: Whether to cancel the task on timeout
    :type cancel_task: bool
    :return: Decorated function
    :rtype: Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]

    Example::

        @with_timeout(5.0)
        async def slow_operation():
            await asyncio.sleep(10)
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError as e:
                msg = error_message or f"Operation timed out after {seconds} seconds"
                raise TimeoutError(msg) from e

        return wrapper

    return decorator


def with_retry(
    max_attempts: int = 3,
    *,
    delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    retry_if: Optional[Callable[[Exception], bool]] = None,
    on_retry: Optional[Callable[[int, Exception], Awaitable[None]]] = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Add retry logic to an async function.

    :param max_attempts: Maximum number of retry attempts
    :type max_attempts: int
    :param delay: Initial delay between retries in seconds
    :type delay: float
    :param max_delay: Maximum delay between retries
    :type max_delay: float
    :param backoff_factor: Multiplicative factor for delay after each retry
    :type backoff_factor: float
    :param exceptions: Tuple of exceptions to catch
    :type exceptions: Tuple[Type[Exception], ...]
    :param retry_if: Optional function to determine if retry should occur
    :type retry_if: Optional[Callable[[Exception], bool]]
    :param on_retry: Optional callback for retry events
    :type on_retry: Optional[Callable[[int, Exception], Awaitable[None]]]
    :return: Decorated function
    :rtype: Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]

    Example::

        @with_retry(max_attempts=3, delay=1.0)
        async def unstable_operation():
            # potentially failing operation
            pass
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_exception: Optional[Exception] = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    should_retry = True

                    if retry_if is not None:
                        should_retry = retry_if(e)

                    if not should_retry or attempt == max_attempts - 1:
                        raise RetryError(
                            f"Failed after {attempt + 1} attempts"
                        ) from last_exception

                    if on_retry is not None:
                        await on_retry(attempt + 1, e)

                    await asyncio.sleep(min(current_delay, max_delay))
                    current_delay *= backoff_factor

            assert last_exception is not None
            raise RetryError(
                f"Failed after {max_attempts} attempts"
            ) from last_exception

        return wrapper

    return decorator


class RateLimiter:
    """Rate limiter implementation using token bucket algorithm."""

    def __init__(self, rate: float, burst: int = 1):
        """
        Initialize rate limiter.

        :param rate: Rate limit (tokens per second)
        :type rate: float
        :param burst: Maximum burst size
        :type burst: int
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire a token from the bucket.

        :raises RateLimitError: If rate limit is exceeded
        """
        async with self._lock:
            now = time.monotonic()
            time_passed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + time_passed * self.rate)

            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                raise RateLimitError(
                    f"Rate limit exceeded. Try again in {wait_time:.2f} seconds"
                )

            self.tokens -= 1
            self.last_update = now


def with_rate_limit(
    rate: float, *, burst: int = 1, limiter: Optional[RateLimiter] = None
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Add rate limiting to an async function.

    :param rate: Rate limit (calls per second)
    :type rate: float
    :param burst: Maximum burst size
    :type burst: int
    :param limiter: Optional custom rate limiter
    :type limiter: Optional[RateLimiter]
    :return: Decorated function
    :rtype: Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]

    Example::

        @with_rate_limit(10.0, burst=5)
        async def limited_operation():
            # operation with rate limit
            pass
    """
    rate_limiter = limiter or RateLimiter(rate, burst)

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            await rate_limiter.acquire()
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_timeout: float = 5.0,
    ):
        """
        Initialize circuit breaker.

        :param failure_threshold: Number of failures before opening circuit
        :type failure_threshold: int
        :param reset_timeout: Time before attempting reset
        :type reset_timeout: float
        :param half_open_timeout: Time to allow testing in half-open state
        :type half_open_timeout: float
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"
        self._lock = asyncio.Lock()

    async def __call__(
        self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute function with circuit breaker logic.

        :param func: Function to execute
        :type func: Callable[..., Awaitable[T]]
        :return: Function result
        :rtype: T
        :raises CircuitBreakerError: If circuit is open
        """
        async with self._lock:
            now = time.monotonic()

            if self.state == "open":
                if (
                    self.last_failure_time is not None
                    and now - self.last_failure_time >= self.reset_timeout
                ):
                    self.state = "half-open"
                else:
                    raise CircuitBreakerError("Circuit breaker is open")

            try:
                if self.state == "half-open":
                    with asyncio.timeout(self.half_open_timeout):
                        result = await func(*args, **kwargs)
                else:
                    result = await func(*args, **kwargs)

                if self.state != "closed":
                    self.state = "closed"
                    self.failures = 0
                return result

            except Exception as e:
                self.failures += 1
                self.last_failure_time = now

                if self.failures >= self.failure_threshold:
                    self.state = "open"

                raise CircuitBreakerError(
                    f"Circuit breaker tripped after {self.failures} failures"
                ) from e


def with_circuit_breaker(
    failure_threshold: int = 5,
    reset_timeout: float = 60.0,
    half_open_timeout: float = 5.0,
    circuit_breaker: Optional[CircuitBreaker] = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Add circuit breaker pattern to an async function.

    :param failure_threshold: Number of failures before opening circuit
    :type failure_threshold: int
    :param reset_timeout: Time before attempting reset
    :type reset_timeout: float
    :param half_open_timeout: Time to allow testing in half-open state
    :type half_open_timeout: float
    :param circuit_breaker: Optional custom circuit breaker
    :type circuit_breaker: Optional[CircuitBreaker]
    :return: Decorated function
    :rtype: Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]

    Example::

        @with_circuit_breaker(failure_threshold=5)
        async def unstable_operation():
            # potentially unstable operation
            pass
    """
    breaker = circuit_breaker or CircuitBreaker(
        failure_threshold, reset_timeout, half_open_timeout
    )

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await breaker(func, *args, **kwargs)

        return wrapper

    return decorator


def with_fallback(
    fallback: Union[Callable[..., Awaitable[T]], T],
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Add fallback logic to an async function.

    :param fallback: Fallback function or value
    :type fallback: Union[Callable[..., Awaitable[T]], T]
    :param exceptions: Exceptions to catch
    :type exceptions: Tuple[Type[Exception], ...]
    :return: Decorated function
    :rtype: Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]

    Example::

        @with_fallback(lambda: "default")
        async def risky_operation():
            # potentially failing operation
            pass
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except exceptions:
                if callable(fallback):
                    try:
                        return await fallback(*args, **kwargs)
                    except Exception as fallback_error:
                        raise FallbackError(
                            "Both main and fallback operations failed"
                        ) from fallback_error
                return cast(T, fallback)

        return wrapper

    return decorator


class Cache:
    """Simple cache implementation with TTL support."""

    def __init__(self, ttl: Optional[float] = None):
        """
        Initialize cache.

        :param ttl: Time to live in seconds
        :type ttl: Optional[float]
        """
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._ttl = ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        :param key: Cache key
        :type key: str
        :return: Cached value or None
        :rtype: Optional[Any]
        """
        async with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]
            if self._ttl is not None and time.monotonic() - timestamp > self._ttl:
                del self._cache[key]
                return None

            return value

    async def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.

        :param key: Cache key
        :type key: str
        :param value: Value to cache
        :type value: Any
        """
        async with self._lock:
            self._cache[key] = (value, time.monotonic())


def with_cache(
    ttl: Optional[float] = None,
    key_func: Optional[Callable[..., str]] = None,
    cache: Optional[Cache] = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Add caching to an async function.

    :param ttl: Cache TTL in seconds
    :type ttl: Optional[float]
    :param key_func: Function to generate cache key
    :type key_func: Optional[Callable[..., str]]
    :param cache: Optional custom cache
    :type cache: Optional[Cache]
    :return: Decorated function
    :rtype: Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]

    Example::

        @with_cache(ttl=60)
        async def expensive_operation(x: int) -> int:
            await asyncio.sleep(1)  # Simulate expensive computation
            return x * 2

        # With custom key function
        @with_cache(key_func=lambda x, y: f"{x}:{y}")
        async def another_operation(x: int, y: int) -> int:
            return x + y
    """
    cache_instance = cache or Cache(ttl)

    def default_key_func(*args: Any, **kwargs: Any) -> str:
        """Generate default cache key from arguments."""
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return ":".join(key_parts)

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key
            key = (key_func or default_key_func)(*args, **kwargs)

            # Try to get from cache
            cached_value = await cache_instance.get(key)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_instance.set(key, result)
            return result

        # Add cache management methods to the wrapper
        wrapper.cache = cache_instance  # type: ignore
        return wrapper

    return decorator


def with_bulk_operations(
    batch_size: int = 100, flush_interval: float = 1.0
) -> Callable[[Callable[..., Awaitable[None]]], Callable[..., Awaitable[None]]]:
    """
    Add bulk operation support to an async function.

    :param batch_size: Maximum batch size
    :type batch_size: int
    :param flush_interval: Maximum time between flushes
    :type flush_interval: float
    :return: Decorated function
    :rtype: Callable[[Callable[..., Awaitable[None]]], Callable[..., Awaitable[None]]]

    Example::

        @with_bulk_operations(batch_size=100)
        async def bulk_insert(items: List[Dict]):
            await db.insert_many(items)
    """

    def decorator(
        func: Callable[[List[Any]], Awaitable[None]]
    ) -> Callable[[Any], Awaitable[None]]:
        batches: Dict[int, List[Any]] = {}
        last_flush_time: Dict[int, float] = {}
        locks: Dict[int, asyncio.Lock] = {}

        async def flush_batch(batch_id: int) -> None:
            """Flush a specific batch."""
            async with locks.get(batch_id, asyncio.Lock()):
                if batch_id in batches and batches[batch_id]:
                    await func(batches[batch_id])
                    batches[batch_id] = []
                    last_flush_time[batch_id] = time.monotonic()

        async def flush_all() -> None:
            """Flush all batches."""
            for batch_id in list(batches.keys()):
                await flush_batch(batch_id)

        @functools.wraps(func)
        async def wrapper(item: Any, batch_id: int = 0) -> None:
            # Initialize batch structures if needed
            if batch_id not in batches:
                batches[batch_id] = []
                last_flush_time[batch_id] = time.monotonic()
                locks[batch_id] = asyncio.Lock()

            # Add item to batch
            async with locks[batch_id]:
                batches[batch_id].append(item)

            # Check if we should flush
            should_flush = False
            async with locks[batch_id]:
                if len(batches[batch_id]) >= batch_size:
                    should_flush = True
                elif time.monotonic() - last_flush_time[batch_id] >= flush_interval:
                    should_flush = True

            if should_flush:
                await flush_batch(batch_id)

        # Add management methods to the wrapper
        wrapper.flush = flush_batch  # type: ignore
        wrapper.flush_all = flush_all  # type: ignore
        return wrapper

    return decorator


def with_profiling(
    logger: Optional[logging.Logger] = None, threshold: Optional[float] = None
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Add execution profiling to an async function.

    :param logger: Logger to use
    :type logger: Optional[logging.Logger]
    :param threshold: Log if execution time exceeds threshold
    :type threshold: Optional[float]
    :return: Decorated function
    :rtype: Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]

    Example::

        @with_profiling(threshold=1.0)
        async def slow_operation():
            await asyncio.sleep(2)
    """
    log = logger or logging.getLogger(__name__)

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.monotonic() - start_time
                if threshold is None or duration >= threshold:
                    log.info(f"{func.__name__} took {duration:.3f} seconds to execute")

        return wrapper

    return decorator


def with_logging(
    logger: Optional[logging.Logger] = None,
    level: int = logging.INFO,
    exc_level: int = logging.ERROR,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Add logging to an async function.

    :param logger: Logger to use
    :type logger: Optional[logging.Logger]
    :param level: Log level for normal execution
    :type level: int
    :param exc_level: Log level for exceptions
    :type exc_level: int
    :return: Decorated function
    :rtype: Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]

    Example::

        @with_logging()
        async def important_operation():
            # operation with logging
            pass
    """
    log = logger or logging.getLogger(__name__)

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                log.log(level, f"Calling {func.__name__}")
                result = await func(*args, **kwargs)
                log.log(level, f"{func.__name__} completed successfully")
                return result
            except Exception as e:
                log.log(exc_level, f"Error in {func.__name__}: {str(e)}")
                raise

        return wrapper

    return decorator
