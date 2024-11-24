"""
Test profiler implementation.
"""

import pytest
import asyncio
from mtaio.monitoring import Profiler


@pytest.mark.asyncio
async def test_profiler_basic():
    """Test basic profiling."""
    profiler = Profiler()

    @profiler.trace
    async def test_function():
        await asyncio.sleep(0.1)
        return 42

    result = await test_function()
    assert result == 42

    profile = await profiler.get_profile()
    assert len(profile.traces) == 1
    assert profile.traces[0].duration >= 0.1


@pytest.mark.asyncio
async def test_profiler_context():
    """Test profiler context manager."""
    profiler = Profiler()

    async with profiler.trace_context("test_operation"):
        await asyncio.sleep(0.1)

    profile = await profiler.get_profile()
    assert len(profile.traces) == 1
    assert profile.traces[0].name == "test_operation"
