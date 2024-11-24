"""
Test resource limiter implementation.
"""

import time
import pytest
import asyncio
from mtaio.resources import RateLimiter, ConcurrencyLimiter
from mtaio.exceptions import ResourceLimitError


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_rate_limiter():
    """Test rate limiting."""
    limiter = RateLimiter(rate=10.0, burst=1)

    await limiter.acquire()

    with pytest.raises(ResourceLimitError):
        await limiter.acquire()

    await asyncio.sleep(1.0)
    await limiter.acquire()


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_rate_limiter_with_burst():
    """Test rate limiter with burst capacity."""
    limiter = RateLimiter(rate=10.0, burst=2)

    await limiter.acquire()
    await limiter.acquire()

    with pytest.raises(ResourceLimitError):
        await limiter.acquire()


@pytest.mark.asyncio
async def test_rate_limiter_wait():
    """Test rate limiter waiting behavior."""
    limiter = RateLimiter(rate=2.0, burst=1)

    await limiter.acquire()
    assert limiter.bucket.tokens < 1

    await asyncio.sleep(0.6)

    start_time = time.monotonic()

    try:
        await limiter.acquire()
    except ResourceLimitError:
        await asyncio.sleep(0.5)
        await limiter.acquire()

    await asyncio.sleep(0.5)
    await limiter.acquire()

    elapsed = time.monotonic() - start_time
    assert elapsed >= 0.4, f"Expected wait time >= 0.4s, got {elapsed}s"


@pytest.mark.asyncio
async def test_concurrency_limiter():
    """Test concurrency limiting."""
    limiter = ConcurrencyLimiter(2)

    async def task():
        async with limiter.acquire():
            await asyncio.sleep(0.1)

    async with asyncio.timeout(1.0):
        tasks = [task() for _ in range(3)]
        await asyncio.gather(*tasks)


@pytest.fixture(autouse=True)
def clean_event_loop():
    """Clean up the event loop after each test"""
    yield
    loop = asyncio.get_event_loop()
    for task in asyncio.all_tasks(loop):
        task.cancel()
