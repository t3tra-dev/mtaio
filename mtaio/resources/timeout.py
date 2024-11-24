"""
Timeout control implementation.

This module provides components for timeout management:

* TimeoutManager: Timeout management
* TimeoutContext: Timeout context manager
* TimeoutGroup: Group timeout control
* TimeoutScheduler: Timeout scheduling
"""

import functools
from typing import (
    AsyncGenerator,
    Dict,
    List,
    NoReturn,
    Set,
    Optional,
    Any,
    Callable,
    Awaitable,
    Type,
    TypeVar,
)
import asyncio
import time
import weakref
import logging
from contextlib import asynccontextmanager

from ..typing import AsyncFunc
from ..exceptions import TimeoutError, TimeoutGroupError

T = TypeVar("T")
logger = logging.getLogger(__name__)


class TimeoutManager:
    """
    Timeout manager implementation.

    Example::

        async with TimeoutManager(5.0) as tm:
            result = await tm.run(long_operation())
            result2 = await tm.run(another_operation(), timeout=2.0)
    """

    def __init__(self, default_timeout: Optional[float] = None):
        """
        Initialize timeout manager.

        :param default_timeout: Default timeout in seconds
        :type default_timeout: Optional[float]
        """
        self.default_timeout = default_timeout
        self._tasks: Set[asyncio.Task] = set()
        self._timeouts: Dict[asyncio.Task, float] = {}
        self._start_times: Dict[asyncio.Task, float] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    async def run(
        self,
        coro: Awaitable[T],
        *,
        timeout: Optional[float] = None,
        propagate: bool = True,
    ) -> T:
        """
        Run coroutine with timeout.

        :param coro: Coroutine to run
        :type coro: Awaitable[T]
        :param timeout: Optional timeout override
        :type timeout: Optional[float]
        :param propagate: Whether to propagate timeout to parent
        :type propagate: bool
        :return: Coroutine result
        :rtype: T
        :raises TimeoutError: If timeout occurs
        """
        timeout = timeout if timeout is not None else self.default_timeout

        task = asyncio.create_task(coro)
        self._tasks.add(task)

        if timeout is not None:
            self._timeouts[task] = timeout
            self._start_times[task] = time.monotonic()

        try:
            return await task
        except asyncio.CancelledError as e:
            if not propagate:
                raise TimeoutError("Operation timed out") from e
            raise
        finally:
            self._tasks.discard(task)
            self._timeouts.pop(task, None)
            self._start_times.pop(task, None)

    async def cancel_on_timeout(self) -> None:
        """Monitor and cancel tasks that exceed their timeout."""
        try:
            while True:
                now = time.monotonic()

                for task in list(self._tasks):
                    if task in self._timeouts:
                        timeout = self._timeouts[task]
                        start_time = self._start_times[task]

                        if now - start_time > timeout:
                            task.cancel()
                            self._tasks.discard(task)
                            self._timeouts.pop(task, None)
                            self._start_times.pop(task, None)

                await asyncio.sleep(0.1)  # Check every 100ms
        except asyncio.CancelledError:
            pass

    async def __aenter__(self) -> "TimeoutManager":
        """Start timeout management."""
        self._cleanup_task = asyncio.create_task(self.cancel_on_timeout())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up timeout management."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)


class TimeoutContext:
    """
    Context manager for timeout control.

    Example::

        async with TimeoutContext(5.0) as ctx:
            # This block will timeout after 5 seconds
            await long_running_operation()

        # Nested timeouts
        async with TimeoutContext(10.0) as outer:
            await operation1()
            async with TimeoutContext(5.0) as inner:
                await operation2()  # This has 5s timeout
            await operation3()  # This has remainder of 10s
    """

    def __init__(
        self,
        timeout: float,
        *,
        propagate: bool = True,
        on_timeout: Optional[Callable[[], Awaitable[None]]] = None,
        exception_type: Type[Exception] = TimeoutError,
        error_message: Optional[str] = None,
    ):
        """
        Initialize timeout context.

        :param timeout: Timeout duration in seconds
        :type timeout: float
        :param propagate: Whether to propagate parent timeout
        :type propagate: bool
        :param on_timeout: Optional callback on timeout
        :type on_timeout: Optional[Callable[[], Awaitable[None]]]
        :param exception_type: Exception type to raise
        :type exception_type: Type[Exception]
        :param error_message: Custom error message
        :type error_message: Optional[str]
        """
        self.timeout = timeout
        self.propagate = propagate
        self.on_timeout = on_timeout
        self.exception_type = exception_type
        self.error_message = error_message
        self._task: Optional[asyncio.Task] = None
        self._timeout_handle: Optional[asyncio.Handle] = None
        self._parent_deadline: Optional[float] = None
        self._deadline: Optional[float] = None
        self._timed_out = False
        self._lock = asyncio.Lock()

    def _get_parent_deadline(self) -> Optional[float]:
        """Get parent context deadline if any."""
        try:
            current_task = asyncio.current_task()
            if current_task and hasattr(current_task, "_timeout_deadline"):
                return getattr(current_task, "_timeout_deadline")
        except Exception:
            pass
        return None

    def _set_task_deadline(self, deadline: float) -> None:
        """Set deadline for current task."""
        try:
            current_task = asyncio.current_task()
            if current_task:
                setattr(current_task, "_timeout_deadline", deadline)
        except Exception:
            pass

    def _clear_task_deadline(self) -> None:
        """Clear deadline from current task."""
        try:
            current_task = asyncio.current_task()
            if current_task and hasattr(current_task, "_timeout_deadline"):
                delattr(current_task, "_timeout_deadline")
        except Exception:
            pass

    def _calculate_deadline(self) -> float:
        """Calculate effective deadline considering parent timeout."""
        now = time.monotonic()
        own_deadline = now + self.timeout

        margin = 0.001 * self.timeout
        own_deadline -= margin

        if self.propagate:
            parent_deadline = self._get_parent_deadline()
            if parent_deadline is not None:
                return min(own_deadline, parent_deadline)

        return own_deadline

    def _raise_timeout(self) -> NoReturn:
        """Raise timeout exception."""
        message = (
            self.error_message or f"Operation timed out after {self.timeout} seconds"
        )
        raise self.exception_type(message)

    async def _handle_timeout(self) -> None:
        """Handle timeout occurrence."""
        async with self._lock:
            if self._timed_out:
                return

            self._timed_out = True

            if self.on_timeout:
                try:
                    await self.on_timeout()
                except Exception as e:
                    logger.error(f"Error in timeout callback: {e}")

            if self._task:
                self._task.cancel()

    def _schedule_timeout(self) -> None:
        """Schedule timeout handler."""
        if self._deadline is None:
            return

        remaining = max(0, self._deadline - time.monotonic())
        loop = asyncio.get_running_loop()
        self._timeout_handle = loop.call_later(
            remaining, lambda: asyncio.create_task(self._handle_timeout())
        )

    def _cancel_timeout(self) -> None:
        """Cancel scheduled timeout."""
        if self._timeout_handle:
            self._timeout_handle.cancel()
            self._timeout_handle = None

    def remaining(self) -> Optional[float]:
        """
        Get remaining time before timeout.

        :return: Remaining seconds or None if no timeout
        :rtype: Optional[float]
        """
        if self._deadline is None:
            return None
        return max(0, self._deadline - time.monotonic())

    def has_expired(self) -> bool:
        """
        Check if timeout has expired.

        :return: True if timeout has expired
        :rtype: bool
        """
        return self._timed_out or (
            self._deadline is not None and time.monotonic() >= self._deadline
        )

    async def check(self) -> None:
        """
        Check and raise if timeout has occurred.

        :raises TimeoutError: If timeout has occurred
        """
        if self.has_expired():
            self._raise_timeout()

    @asynccontextmanager
    async def timeout(self, timeout: Optional[float]) -> AsyncGenerator[None, None]:
        """
        Nested timeout context.

        :param timeout: Timeout duration in seconds
        :type timeout: Optional[float]
        """
        if timeout is None:
            yield
            return

        child_context = TimeoutContext(
            timeout,
            propagate=self.propagate,
            on_timeout=self.on_timeout,
            exception_type=self.exception_type,
        )
        async with child_context:
            yield

    async def __aenter__(self) -> "TimeoutContext":
        """Enter timeout context."""
        self._parent_deadline = self._get_parent_deadline()
        self._deadline = self._calculate_deadline()
        self._task = asyncio.current_task()

        if self._deadline is not None:
            self._set_task_deadline(self._deadline)
            self._schedule_timeout()

        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> Optional[bool]:
        """Exit timeout context."""
        self._cancel_timeout()
        self._clear_task_deadline()

        if self._parent_deadline is not None:
            self._set_task_deadline(self._parent_deadline)

        if isinstance(exc_val, asyncio.CancelledError) and self._timed_out:
            self._raise_timeout()

        return None


class ContextTimeout:
    """
    Alternative timeout context with async context manager.

    Example::

        timeout_ctx = ContextTimeout()

        @timeout_ctx.timeout(5.0)
        async def operation():
            await long_running_task()
    """

    def timeout(
        self, seconds: float, *, error_message: Optional[str] = None
    ) -> Callable[[AsyncFunc[T]], AsyncFunc[T]]:
        """
        Timeout decorator.

        :param seconds: Timeout duration in seconds
        :type seconds: float
        :param error_message: Custom error message
        :type error_message: Optional[str]
        :return: Decorated function
        :rtype: Callable[[AsyncFunc[T]], AsyncFunc[T]]
        """

        def decorator(func: AsyncFunc[T]) -> AsyncFunc[T]:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                async with TimeoutContext(seconds, error_message=error_message):
                    return await func(*args, **kwargs)

            return wrapper

        return decorator

    @asynccontextmanager
    async def deadline(self, deadline: float) -> AsyncGenerator[None, None]:
        """
        Context manager with absolute deadline.

        :param deadline: Absolute timestamp for deadline
        :type deadline: float
        """
        now = time.monotonic()
        timeout = max(0, deadline - now)

        async with TimeoutContext(timeout):
            yield

    @asynccontextmanager
    async def optional_timeout(
        self, timeout: Optional[float]
    ) -> AsyncGenerator[None, None]:
        """
        Context manager with optional timeout.

        :param timeout: Optional timeout duration
        :type timeout: Optional[float]
        """
        if timeout is None:
            yield
        else:
            async with TimeoutContext(timeout):
                yield


class TimeoutGroup:
    """
    Group timeout control.

    Example::

        async with TimeoutGroup() as group:
            task1 = group.create_task(operation1(), timeout=5.0)
            task2 = group.create_task(operation2(), timeout=3.0)
            results = await group.gather()
    """

    def __init__(self):
        """Initialize timeout group."""
        self._tasks: Dict[asyncio.Task, float] = {}
        self._start_times: Dict[asyncio.Task, float] = {}
        self._results: Dict[asyncio.Task, Any] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._closed = False

    def create_task(
        self,
        coro: Awaitable[T],
        *,
        timeout: Optional[float] = None,
        name: Optional[str] = None,
    ) -> asyncio.Task[T]:
        """
        Create task with timeout.

        :param coro: Coroutine to run
        :type coro: Awaitable[T]
        :param timeout: Optional timeout
        :type timeout: Optional[float]
        :param name: Optional task name
        :type name: Optional[str]
        :return: Created task
        :rtype: asyncio.Task[T]
        """
        if self._closed:
            raise TimeoutGroupError("Group is closed")

        task = asyncio.create_task(coro, name=name)

        if timeout is not None:
            self._tasks[task] = timeout
            self._start_times[task] = time.monotonic()

        return task

    async def gather(self, *, return_exceptions: bool = False) -> List[Any]:
        """
        Gather all task results.

        :param return_exceptions: Whether to return exceptions
        :type return_exceptions: bool
        :return: List of results
        :rtype: List[Any]
        """
        if not self._tasks:
            return []

        try:
            results = await asyncio.gather(
                *self._tasks.keys(), return_exceptions=return_exceptions
            )
            return results
        finally:
            self._closed = True

    async def cancel_on_timeout(self) -> None:
        """Monitor and cancel tasks that exceed their timeout."""
        try:
            while not self._closed:
                now = time.monotonic()

                for task, timeout in list(self._tasks.items()):
                    start_time = self._start_times[task]
                    if now - start_time > timeout:
                        task.cancel()
                        self._tasks.pop(task, None)
                        self._start_times.pop(task, None)

                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass

    async def __aenter__(self) -> "TimeoutGroup":
        """Start timeout group."""
        self._cleanup_task = asyncio.create_task(self.cancel_on_timeout())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up timeout group."""
        self._closed = True
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


class TimeoutScheduler:
    """
    Timeout scheduling implementation.

    Example::

        scheduler = TimeoutScheduler()

        @scheduler.schedule(timeout=5.0)
        async def scheduled_operation():
            await long_running_task()
    """

    def __init__(self):
        """Initialize timeout scheduler."""
        self._tasks: weakref.WeakSet[asyncio.Task] = weakref.WeakSet()
        self._timeouts: Dict[asyncio.Task, float] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    def schedule(
        self,
        timeout: float,
        retry: bool = False,
        max_retries: int = 3,
        backoff: float = 1.0,
    ) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
        """
        Schedule function with timeout.

        :param timeout: Timeout in seconds
        :type timeout: float
        :param retry: Whether to retry on timeout
        :type retry: bool
        :param max_retries: Maximum retry attempts
        :type max_retries: int
        :param backoff: Retry backoff factor
        :type backoff: float
        :return: Decorator function
        :rtype: Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]
        """

        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                retries = 0
                current_timeout = timeout

                while True:
                    try:
                        task = asyncio.create_task(func(*args, **kwargs))
                        self._tasks.add(task)
                        self._timeouts[task] = current_timeout

                        result = await asyncio.wait_for(task, current_timeout)
                        self._timeouts.pop(task, None)
                        return result

                    except asyncio.TimeoutError:
                        if not retry or retries >= max_retries:
                            raise TimeoutError(
                                f"Operation timed out after {retries + 1} attempts"
                            )
                        retries += 1
                        current_timeout *= backoff

                    finally:
                        if task in self._timeouts:
                            self._timeouts.pop(task)

            return wrapper

        return decorator

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self) -> None:
        """Clean up expired tasks."""
        try:
            while self._running:
                for task in list(self._tasks):
                    if task.done():
                        self._timeouts.pop(task, None)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass


@asynccontextmanager
async def timeout(seconds: float) -> AsyncGenerator[None, None]:
    """
    Simple timeout context manager.

    Example::

        async with timeout(5.0):
            await long_running_operation()

    :param seconds: Timeout in seconds
    :type seconds: float
    :raises TimeoutError: If timeout occurs
    """
    try:
        yield await asyncio.wait_for(asyncio.sleep(0), timeout=0)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
