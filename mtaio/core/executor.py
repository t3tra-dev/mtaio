"""
Core task execution functionality for mtaio.
Provides utilities for executing multiple coroutines concurrently with optional limits.
"""

from typing import Any, Awaitable, Callable, Coroutine, List, Optional, TypeVar
import asyncio
import concurrent.futures
from functools import partial

from ..exceptions import ExecutionError
from ..typing import AsyncCallable

T = TypeVar("T")


class TaskExecutor:
    """
    Executes multiple coroutines concurrently with optional concurrency limits.

    :Example:

    .. code-block:: python

        executor = TaskExecutor()
        results = await executor.gather(coro1(), coro2(), limit=5)
    """

    def __init__(
        self, thread_pool: Optional[concurrent.futures.ThreadPoolExecutor] = None
    ):
        """
        Initialize the TaskExecutor.

        :param thread_pool: Optional thread pool for executing synchronous functions.
                          If None, a new thread pool will be created when needed.
        :type thread_pool: Optional[concurrent.futures.ThreadPoolExecutor]
        """
        self._thread_pool = thread_pool
        self._active_tasks: set[asyncio.Task] = set()

    async def run(
        self,
        coro: Awaitable[T],
        *,
        timeout: Optional[float] = None
    ) -> T:
        """Run coroutine with timeout."""
        if timeout is not None:
            return await asyncio.wait_for(coro, timeout)
        return await coro

    async def gather(
        self,
        *coroutines: Coroutine[Any, Any, T],
        limit: Optional[int] = None,
        return_exceptions: bool = False,
    ) -> List[T]:
        """
        Execute multiple coroutines concurrently with an optional concurrency limit.

        :param coroutines: Coroutines to execute
        :type coroutines: Coroutine[Any, Any, T]
        :param limit: Maximum number of coroutines to execute simultaneously
        :type limit: Optional[int]
        :param return_exceptions: If True, exceptions are returned rather than raised
        :type return_exceptions: bool
        :return: List of results from the coroutines in the order they were passed
        :rtype: List[T]
        :raises ExecutionError: If any coroutine fails and return_exceptions is False
        """
        if not coroutines:
            return []

        if limit is None or limit <= 0:
            return await asyncio.gather(
                *coroutines, return_exceptions=return_exceptions
            )

        async def run_limited():
            semaphore = asyncio.Semaphore(limit)

            async def run_with_semaphore(coro: Coroutine[Any, Any, T]) -> T:
                async with semaphore:
                    return await coro

            return await asyncio.gather(
                *(run_with_semaphore(coro) for coro in coroutines),
                return_exceptions=return_exceptions,
            )

        try:
            return await run_limited()
        except Exception as e:
            if return_exceptions:
                return [e]
            raise ExecutionError("Error executing coroutines") from e

    async def run_in_thread(
        self, func: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute a synchronous function in a separate thread.

        :param func: The synchronous function to execute
        :type func: Callable[..., T]
        :param args: Positional arguments to pass to the function
        :type args: Any
        :param kwargs: Keyword arguments to pass to the function
        :type kwargs: Any
        :return: The result of the function execution
        :rtype: T
        :raises ExecutionError: If the function execution fails
        """
        if self._thread_pool is None:
            self._thread_pool = concurrent.futures.ThreadPoolExecutor()

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                self._thread_pool, partial(func, *args, **kwargs)
            )
        except Exception as e:
            raise ExecutionError(f"Error executing {func.__name__} in thread") from e

    async def map(
        self,
        func: AsyncCallable[T],
        *iterables: Any,
        limit: Optional[int] = None,
        return_exceptions: bool = False,
    ) -> List[T]:
        """
        Apply a function to every item of iterables concurrently.

        :param func: The function (coroutine or regular) to apply
        :type func: Union[CoroFunc[T], Callable[..., T]]
        :param iterables: Input iterables
        :type iterables: Any
        :param limit: Maximum number of concurrent executions
        :type limit: Optional[int]
        :param return_exceptions: If True, exceptions are returned rather than raised
        :type return_exceptions: bool
        :return: List of results in the order of input iterables
        :rtype: List[T]
        """
        if asyncio.iscoroutinefunction(func):
            coroutines = [func(*args) for args in zip(*iterables)]
            return await self.gather(
                *coroutines, limit=limit, return_exceptions=return_exceptions
            )
        else:

            async def wrapper(*args):
                return await self.run_in_thread(func, *args)

            coroutines = [wrapper(*args) for args in zip(*iterables)]
            return await self.gather(
                *coroutines, limit=limit, return_exceptions=return_exceptions
            )

    def create_task(self, coro: Coroutine[Any, Any, T]) -> asyncio.Task[T]:
        """
        Create a new task from a coroutine and track it.

        :param coro: The coroutine to convert into a task
        :type coro: Coroutine[Any, Any, T]
        :return: The created task
        :rtype: asyncio.Task[T]
        """
        task = asyncio.create_task(coro)
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
        return task

    async def cancel_all(self) -> None:
        """
        Cancel all active tasks being tracked by this executor.
        """
        for task in self._active_tasks:
            task.cancel()

        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        self._active_tasks.clear()

    async def __aenter__(self) -> "TaskExecutor":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.cancel_all()
        if self._thread_pool is not None:
            self._thread_pool.shutdown(wait=True)
