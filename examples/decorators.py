"""
Decorator usage examples for mtaio library.

This example demonstrates:
- Async adapter decorators
- Control flow decorators
- Caching decorators
"""

import asyncio
import random
import time
from mtaio.cache.ttl import TTLCache
from mtaio.decorators import (
    async_adapter,
    with_timeout,
    with_retry,
    with_rate_limit,
    with_cache,
    with_circuit_breaker,
)
from mtaio.exceptions import CircuitBreakerError, RetryError
from mtaio.resources.limiter import RateLimiter


# Sync to async conversion example
@async_adapter
def cpu_intensive(data: str) -> str:
    """
    Simulate CPU-intensive operation.

    :param data: Input data
    :return: Processed data
    """
    time.sleep(0.1)  # Simulate processing
    return f"Processed: {data}"


# Timeout control example
@with_timeout(2.0, error_message="Operation took too long")
async def slow_operation() -> str:
    """
    Simulate slow operation with timeout.

    :return: Operation result
    :raises TimeoutError: If operation exceeds timeout
    """
    await asyncio.sleep(1.5)
    return "Operation completed"


# Retry logic example
@with_retry(max_attempts=3, delay=1.0)
async def unstable_operation() -> str:
    """
    Simulate unstable operation with retries.

    :return: Operation result
    :raises RetryError: If all retries fail
    """
    if random.random() < 0.7:  # 70% chance of failure
        raise ConnectionError("Random failure")
    return "Operation succeeded"


# Rate limiting example
limiter = RateLimiter(2.0)  # 2 operations per second


@with_rate_limit(2.0)
async def rate_limited_operation(item: str) -> str:
    """
    Rate-limited operation example.

    :param item: Input item
    :return: Processed item
    """
    await asyncio.sleep(0.1)
    return f"Processed {item}"


# Caching example
cache = TTLCache[str](default_ttl=60.0)


@with_cache(cache)
async def expensive_operation(param: str) -> str:
    """
    Expensive operation with caching.

    :param param: Input parameter
    :return: Operation result
    """
    await asyncio.sleep(1.0)  # Simulate expensive computation
    return f"Result for {param}"


# Circuit breaker example
@with_circuit_breaker(failure_threshold=3, reset_timeout=5.0)
async def fragile_operation() -> str:
    """
    Operation protected by circuit breaker.

    :return: Operation result
    :raises CircuitBreakerError: If circuit is open
    """
    if random.random() < 0.6:  # 60% chance of failure
        raise ConnectionError("Service unavailable")
    return "Operation succeeded"


async def decorator_examples() -> None:
    """
    Run examples of different decorators.
    """
    # Async adapter
    result = await cpu_intensive("test data")
    print(f"Async adapter result: {result}")

    # Timeout control
    try:
        result = await slow_operation()
        print(f"Timeout operation result: {result}")
    except TimeoutError as e:
        print(f"Timeout occurred: {e}")

    # Retry logic
    try:
        result = await unstable_operation()
        print(f"Retry operation result: {result}")
    except RetryError as e:
        print(f"Retry failed: {e}")

    # Rate limiting
    items = ["item1", "item2", "item3", "item4"]
    for item in items:
        result = await rate_limited_operation(item)
        print(f"Rate limited result: {result}")

    # Caching
    params = ["param1", "param1", "param2"]  # Note: param1 is repeated
    for param in params:
        start_time = time.monotonic()
        result = await expensive_operation(param)
        duration = time.monotonic() - start_time
        print(f"Cache operation result: {result} (took {duration:.2f}s)")

    # Circuit breaker
    for _ in range(5):
        try:
            result = await fragile_operation()
            print(f"Circuit breaker result: {result}")
        except CircuitBreakerError as e:
            print(f"Circuit breaker: {e}")


async def main() -> None:
    """
    Run all decorator examples.
    """
    await decorator_examples()


if __name__ == "__main__":
    asyncio.run(main())
