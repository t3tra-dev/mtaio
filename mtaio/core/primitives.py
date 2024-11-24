"""
Core asynchronous primitives for mtaio.

This module provides fundamental asynchronous data structures and synchronization primitives:

* AsyncQueue: Base asynchronous queue implementation
* PriorityQueue: Priority-based asynchronous queue
* LIFOQueue: Last-In-First-Out asynchronous queue
* Latch: Countdown synchronization primitive
"""

from typing import Optional, Generic, TypeVar
import asyncio
import heapq
import time
from dataclasses import dataclass, field

T = TypeVar("T")


class AsyncQueue(Generic[T]):
    """
    Base implementation of an asynchronous queue.

    :param maxsize: The maximum size of the queue. If 0, the queue size is unlimited.
    :type maxsize: int

    Example::

        queue = AsyncQueue[int](maxsize=10)
        await queue.put(1)
        item = await queue.get()
    """

    def __init__(self, maxsize: int = 0):
        """
        Initialize the queue.

        :param maxsize: Maximum queue size (0 for unlimited)
        """
        self._maxsize = maxsize
        self._queue: list[T] = []
        self._getters: list[asyncio.Future[T]] = []
        self._putters: list[tuple[T, asyncio.Future[None]]] = []
        self._unfinished_tasks = 0
        self._finished = asyncio.Event()
        self._finished.set()

    def qsize(self) -> int:
        """
        Return the current size of the queue.

        :return: Current number of items in the queue
        :rtype: int
        """
        return len(self._queue)

    def empty(self) -> bool:
        """
        Check if the queue is empty.

        :return: True if the queue is empty, False otherwise
        :rtype: bool
        """
        return not self._queue

    def full(self) -> bool:
        """
        Check if the queue is full.

        :return: True if the queue is full, False otherwise
        :rtype: bool
        """
        if self._maxsize <= 0:
            return False
        return self.qsize() >= self._maxsize

    async def put(self, item: T) -> None:
        """
        Put an item into the queue.

        If the queue is full, wait until a free slot is available.

        :param item: Item to put into the queue
        :type item: T
        :raises asyncio.CancelledError: If the operation is cancelled
        """
        while self.full():
            putter = asyncio.get_running_loop().create_future()
            self._putters.append((item, putter))
            try:
                await putter
            except Exception:
                self._putters.remove((item, putter))
                raise

        self._put(item)
        self._unfinished_tasks += 1
        self._finished.clear()
        self._wakeup_next_waiter()

    def _put(self, item: T) -> None:
        """
        Put an item into the queue (no waiting).

        :param item: Item to put into the queue
        :type item: T
        """
        self._queue.append(item)

    async def get(self) -> T:
        """
        Remove and return an item from the queue.

        If queue is empty, wait until an item is available.

        :return: Next item from the queue
        :rtype: T
        :raises asyncio.CancelledError: If the operation is cancelled
        """
        while self.empty():
            getter = asyncio.get_running_loop().create_future()
            self._getters.append(getter)
            try:
                return await getter
            except Exception:
                self._getters.remove(getter)
                raise

        item = self._get()
        self._wakeup_next_waiter()
        return item

    def _get(self) -> T:
        """
        Get an item from the queue (no waiting).

        :return: Next item from the queue
        :rtype: T
        """
        return self._queue.pop(0)

    def task_done(self) -> None:
        """
        Indicate that a formerly enqueued task is complete.

        :raises ValueError: If called more times than there were items placed in the queue
        """
        if self._unfinished_tasks <= 0:
            raise ValueError("task_done() called too many times")
        self._unfinished_tasks -= 1
        if self._unfinished_tasks == 0:
            self._finished.set()

    async def join(self) -> None:
        """
        Wait until all items in the queue have been processed.
        """
        if self._unfinished_tasks > 0:
            await self._finished.wait()

    def _wakeup_next_waiter(self) -> None:
        """Wake up the next waiter if one exists."""
        while self._putters and not self.full():
            item, putter = self._putters.pop(0)
            if not putter.done():
                self._put(item)
                putter.set_result(None)
                return

        while self._getters and not self.empty():
            getter = self._getters.pop(0)
            if not getter.done():
                getter.set_result(self._get())
                return


@dataclass(order=True)
class _PrioritizedItem(Generic[T]):
    """Wrapper for items with priority."""

    priority: float
    count: int
    item: T = field(compare=False)


class PriorityQueue(AsyncQueue[T]):
    """
    Priority queue implementation.

    Items are retrieved based on their priority (lowest number = highest priority).

    Example::

        pq = PriorityQueue[str]()
        await pq.put("task", priority=1)
        item = await pq.get()  # Returns highest priority item
    """

    def __init__(self, maxsize: int = 0):
        """
        Initialize the priority queue.

        :param maxsize: Maximum queue size (0 for unlimited)
        :type maxsize: int
        """
        super().__init__(maxsize)
        self._queue: list[_PrioritizedItem[T]] = []
        self._count = 0

    async def put(self, item: T, priority: float = 0) -> None:
        """
        Put an item into the queue with a priority.

        :param item: Item to put into the queue
        :type item: T
        :param priority: Priority of the item (lower number = higher priority)
        :type priority: float
        """
        prioritized = _PrioritizedItem(priority, self._count, item)
        self._count += 1
        await super().put(prioritized)

    def _put(self, item: _PrioritizedItem[T]) -> None:
        """Insert item into the priority queue."""
        heapq.heappush(self._queue, item)

    def _get(self) -> T:
        """Remove and return the item with highest priority."""
        return heapq.heappop(self._queue).item


class LIFOQueue(AsyncQueue[T]):
    """
    Last-In-First-Out (LIFO) queue implementation.

    Example::

        stack = LIFOQueue[int]()
        await stack.put(1)
        await stack.put(2)
        item = await stack.get()  # Returns 2
    """

    def _get(self) -> T:
        """Remove and return the most recently added item."""
        return self._queue.pop()


class Latch:
    """
    Countdown latch implementation.

    A synchronization primitive that allows one or more tasks to wait until
    a set of operations being performed in other tasks completes.

    Example::

        latch = Latch(3)
        await latch.count_down()  # Decrease counter
        await latch.wait()  # Wait until counter reaches 0
    """

    def __init__(self, count: int):
        """
        Initialize the latch.

        :param count: Initial count
        :type count: int
        :raises ValueError: If count is less than 0
        """
        if count < 0:
            raise ValueError("Latch count cannot be negative")
        self._count = count
        self._condition = asyncio.Condition()

    async def count_down(self) -> None:
        """
        Decrease the count of the latch by one.

        If the count reaches zero, all waiting tasks are notified.
        """
        async with self._condition:
            if self._count > 0:
                self._count -= 1
                if self._count == 0:
                    self._condition.notify_all()

    async def wait(self, timeout: Optional[float] = None) -> bool:
        """
        Wait until the count reaches zero.

        :param timeout: Maximum time to wait in seconds
        :type timeout: float or None
        :return: True if the count reached zero, False if timeout occurred
        :rtype: bool
        """
        deadline = None if timeout is None else time.monotonic() + timeout

        async with self._condition:
            while self._count > 0:
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return False
                    try:
                        await asyncio.wait_for(self._condition.wait(), remaining)
                    except asyncio.TimeoutError:
                        return False
                else:
                    await self._condition.wait()
            return True

    def get_count(self) -> int:
        """
        Get the current count.

        :return: Current count
        :rtype: int
        """
        return self._count
