"""
Test task executor implementation.
"""

import pytest
import asyncio
from mtaio.core import TaskExecutor
from mtaio.exceptions import ExecutionError


@pytest.mark.asyncio
async def test_task_executor_gather():
    """Test task executor gather operation."""
    executor = TaskExecutor()

    async def task(x: int) -> int:
        await asyncio.sleep(0.1)
        return x * 2

    results = await executor.gather(
        task(1),
        task(2),
        task(3)
    )

    assert sorted(results) == [2, 4, 6]


@pytest.mark.asyncio
async def test_task_executor_timeout():
    """Test task executor timeout."""
    executor = TaskExecutor()

    async def slow_task() -> None:
        await asyncio.sleep(1.0)

    with pytest.raises((TimeoutError, ExecutionError)):
        await executor.run(slow_task(), timeout=0.1)
