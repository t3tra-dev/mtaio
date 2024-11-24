"""
Resource management examples for mtaio library.

This example demonstrates:
- Rate limiting
- Timeout management
- Concurrency control
"""

import asyncio
from typing import Optional
from mtaio.resources import (
    RateLimiter,
    TimeoutManager,
    ConcurrencyLimiter,
)
from mtaio.exceptions import (
    ResourceLimitError,
    TimeoutError,
)


async def rate_limit_example() -> None:
    """
    Demonstrates rate limiting functionality.
    """
    # Create rate limiter (2 operations per second)
    limiter = RateLimiter(2.0)

    @limiter.limit
    async def rate_limited_operation(item: str) -> None:
        """Rate-limited operation."""
        print(f"Processing {item}")
        await asyncio.sleep(0.1)

    try:
        # Try to process items faster than rate limit
        items = [f"item{i}" for i in range(5)]
        for item in items:
            await rate_limited_operation(item)

    except ResourceLimitError as e:
        print(f"Rate limit exceeded: {e}")


async def timeout_example() -> None:
    """
    Demonstrates timeout management.
    """

    async def slow_operation() -> str:
        """Simulate slow operation."""
        await asyncio.sleep(2.0)
        return "Operation complete"

    async def fast_operation() -> str:
        """Simulate fast operation."""
        await asyncio.sleep(0.5)
        return "Operation complete"

    # Use timeout manager
    async with TimeoutManager(default_timeout=1.0) as tm:
        try:
            # This should succeed
            result = await tm.run(fast_operation())
            print(f"Fast operation: {result}")

            # This should timeout
            result = await tm.run(slow_operation())
            print(f"Slow operation: {result}")

        except TimeoutError as e:
            print(f"Timeout occurred: {e}")


async def concurrency_example() -> None:
    """
    Demonstrates concurrency limiting.
    """
    # Create concurrency limiter (max 2 concurrent operations)
    limiter = ConcurrencyLimiter(2)

    async def concurrent_operation(task_id: int) -> None:
        """
        Operation with concurrency limit.

        :param task_id: Task identifier
        """
        print(f"Task {task_id} started")
        await asyncio.sleep(1.0)
        print(f"Task {task_id} completed")

    # Create tasks
    tasks = []
    for i in range(5):
        task = limiter.limit(concurrent_operation)(i)
        tasks.append(task)

    # Run tasks with concurrency limit
    await asyncio.gather(*tasks)


class ResourcePool:
    """
    Example of custom resource pool implementation.
    """

    def __init__(self, size: int):
        """
        Initialize resource pool.

        :param size: Pool size
        """
        self.size = size
        self.available = asyncio.Semaphore(size)
        self.resources: set[int] = set(range(size))
        self.lock = asyncio.Lock()

    async def acquire(self) -> Optional[int]:
        """
        Acquire resource from pool.

        :return: Resource identifier or None if none available
        """
        if not await self.available.acquire():
            return None

        async with self.lock:
            if not self.resources:
                self.available.release()
                return None
            return self.resources.pop()

    async def release(self, resource_id: int) -> None:
        """
        Release resource back to pool.

        :param resource_id: Resource identifier
        """
        async with self.lock:
            self.resources.add(resource_id)
            self.available.release()


async def resource_pool_example() -> None:
    """
    Demonstrates resource pool usage.
    """
    pool = ResourcePool(2)

    async def worker(worker_id: int) -> None:
        """
        Worker that uses pool resource.

        :param worker_id: Worker identifier
        """
        # Acquire resource
        resource_id = await pool.acquire()
        if resource_id is not None:
            try:
                print(f"Worker {worker_id} using resource {resource_id}")
                await asyncio.sleep(1.0)
            finally:
                await pool.release(resource_id)
                print(f"Worker {worker_id} released resource {resource_id}")

    # Run workers
    workers = [worker(i) for i in range(4)]
    await asyncio.gather(*workers)


async def combined_example() -> None:
    """
    Demonstrates combining multiple resource controls.
    """
    rate_limiter = RateLimiter(2.0)
    concurrency_limiter = ConcurrencyLimiter(2)

    @rate_limiter.limit
    @concurrency_limiter.limit
    async def controlled_operation(task_id: int) -> None:
        """
        Operation with both rate and concurrency limits.

        :param task_id: Task identifier
        """
        print(f"Task {task_id} started")
        await asyncio.sleep(0.5)
        print(f"Task {task_id} completed")

    # Run multiple tasks
    tasks = [controlled_operation(i) for i in range(5)]
    await asyncio.gather(*tasks)


async def main() -> None:
    """
    Run all resource management examples.
    """
    print("=== Rate Limit Example ===")
    await rate_limit_example()

    print("\n=== Timeout Example ===")
    await timeout_example()

    print("\n=== Concurrency Example ===")
    await concurrency_example()

    print("\n=== Resource Pool Example ===")
    await resource_pool_example()

    print("\n=== Combined Example ===")
    await combined_example()


if __name__ == "__main__":
    asyncio.run(main())
