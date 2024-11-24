"""
Asynchronous stream processing implementation.

This module provides tools for working with asynchronous data streams:

* Stream: Base class for asynchronous data streams
* Operator: Base class for stream operators
* StreamSource: Base class for stream sources
* StreamSink: Base class for stream sinks
"""

from typing import (
    Iterable,
    TypeVar,
    Protocol,
    AsyncIterator,
    AsyncIterable,
    Callable,
    Awaitable,
    Optional,
    Union,
    List,
    Any,
    runtime_checkable,
)
import asyncio
from collections import deque
from ..exceptions import StreamError

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


@runtime_checkable
class Operator(Protocol[T, U]):
    """
    Protocol defining the interface for stream operators.
    """

    async def process(self, item: T) -> Optional[U]:
        """
        Process a single item in the stream.

        :param item: Item to process
        :type item: T
        :return: Processed item or None if item should be filtered out
        :rtype: Optional[U]
        """
        ...

    async def setup(self) -> None:
        """Set up the operator."""
        ...

    async def cleanup(self) -> None:
        """Clean up the operator."""
        ...


class Stream(AsyncIterable[T]):
    """
    Base class for asynchronous data streams.

    Example::

        stream = Stream.from_iterable([1, 2, 3, 4, 5])
        result = await (stream
            .map(lambda x: x * 2)
            .filter(lambda x: x > 5)
            .reduce(lambda acc, x: acc + x))
    """

    def __init__(self, source: AsyncIterable[T]):
        """
        Initialize the stream.

        :param source: Source of stream items
        :type source: AsyncIterable[T]
        """
        self._source = source
        self._operators: List[Operator] = []

    @classmethod
    def from_iterable(
        cls, iterable: Union[Iterable[T], AsyncIterable[T]]
    ) -> "Stream[T]":
        """
        Create a stream from an iterable.

        :param iterable: Source iterable
        :type iterable: Union[Iterable[T], AsyncIterable[T]]
        :return: New stream
        :rtype: Stream[T]
        """

        async def aiter_wrapper():
            if isinstance(iterable, AsyncIterable):
                async for item in iterable:
                    yield item
            else:
                for item in iterable:
                    yield item

        return cls(aiter_wrapper())

    async def __aiter__(self) -> AsyncIterator[T]:
        """
        Iterate over the stream items.

        :return: Stream iterator
        :rtype: AsyncIterator[T]
        """

        async def process_item(item: Any, ops: List[Operator]) -> Optional[Any]:
            current = item
            for op in ops:
                if current is None:
                    return None
                current = await op.process(current)
            return current

        # Set up operators
        for op in self._operators:
            await op.setup()

        try:
            async for item in self._source:
                result = await process_item(item, self._operators)
                if result is not None:
                    yield result
        finally:
            # Clean up operators
            for op in reversed(self._operators):
                await op.cleanup()

    def add_operator(self, operator: Operator[T, U]) -> "Stream[U]":
        """
        Add an operator to the stream.

        :param operator: Operator to add
        :type operator: Operator[T, U]
        :return: New stream with operator added
        :rtype: Stream[U]
        """
        new_stream = Stream(self)
        new_stream._operators = self._operators + [operator]
        return new_stream

    def map(
        self, func: Union[Callable[[T], U], Callable[[T], Awaitable[U]]]
    ) -> "Stream[U]":
        """
        Transform items using a mapping function.

        :param func: Mapping function
        :type func: Union[Callable[[T], U], Callable[[T], Awaitable[U]]]
        :return: New stream with mapping applied
        :rtype: Stream[U]
        """

        class MapOperator(Operator[T, U]):
            async def process(self, item: T) -> U:
                result = func(item)
                if asyncio.iscoroutine(result):
                    result = await result
                return result

            async def setup(self) -> None:
                pass

            async def cleanup(self) -> None:
                pass

        return self.add_operator(MapOperator())

    def filter(
        self, predicate: Union[Callable[[T], bool], Callable[[T], Awaitable[bool]]]
    ) -> "Stream[T]":
        """
        Filter items using a predicate.

        :param predicate: Filter predicate
        :type predicate: Union[Callable[[T], bool], Callable[[T], Awaitable[bool]]]
        :return: New stream with filter applied
        :rtype: Stream[T]
        """

        class FilterOperator(Operator[T, T]):
            async def process(self, item: T) -> Optional[T]:
                result = predicate(item)
                if asyncio.iscoroutine(result):
                    result = await result
                return item if result else None

            async def setup(self) -> None:
                pass

            async def cleanup(self) -> None:
                pass

        return self.add_operator(FilterOperator())

    async def reduce(
        self,
        func: Union[Callable[[U, T], U], Callable[[U, T], Awaitable[U]]],
        initial: Optional[U] = None,
    ) -> U:
        """
        Reduce the stream to a single value.

        :param func: Reduction function
        :type func: Union[Callable[[U, T], U], Callable[[U, T], Awaitable[U]]]
        :param initial: Initial value
        :type initial: Optional[U]
        :return: Reduced value
        :rtype: U
        """
        result = initial
        first = True

        async for item in self:
            if first and result is None:
                result = item
                first = False
            else:
                current_result = func(result, item)
                if asyncio.iscoroutine(current_result):
                    result = await current_result
                else:
                    result = current_result

        if first and result is None:
            raise StreamError("Empty stream with no initial value")

        return result

    def batch(self, size: int) -> "Stream[List[T]]":
        """
        Group items into batches.

        :param size: Batch size
        :type size: int
        :return: New stream of batches
        :rtype: Stream[List[T]]
        """

        class BatchOperator(Operator[T, List[T]]):
            def __init__(self, size: int):
                self.size = size
                self.batch: List[T] = []

            async def process(self, item: T) -> Optional[List[T]]:
                self.batch.append(item)
                if len(self.batch) >= self.size:
                    result = self.batch
                    self.batch = []
                    return result
                return None

            async def cleanup(self) -> Optional[List[T]]:
                if self.batch:
                    return self.batch
                return None

            async def setup(self) -> None:
                self.batch = []

        return self.add_operator(BatchOperator(size))

    def window(self, size: int, step: int = 1) -> "Stream[List[T]]":
        """
        Create sliding windows of items.

        :param size: Window size
        :type size: int
        :param step: Window step size
        :type step: int
        :return: New stream of windows
        :rtype: Stream[List[T]]
        """

        class WindowOperator(Operator[T, List[T]]):
            def __init__(self, size: int, step: int):
                self.size = size
                self.step = step
                self.window: deque[T] = deque(maxlen=size)
                self.count = 0

            async def process(self, item: T) -> Optional[List[T]]:
                self.window.append(item)
                self.count += 1
                if (
                    len(self.window) == self.size
                    and (self.count - self.size) % self.step == 0
                ):
                    return list(self.window)
                return None

            async def setup(self) -> None:
                self.window.clear()
                self.count = 0

            async def cleanup(self) -> None:
                pass

        return self.add_operator(WindowOperator(size, step))

    def distinct(self) -> "Stream[T]":
        """
        Remove duplicate items from the stream.

        :return: New stream with duplicates removed
        :rtype: Stream[T]
        """

        class DistinctOperator(Operator[T, T]):
            def __init__(self):
                self.seen = set()

            async def process(self, item: T) -> Optional[T]:
                if item not in self.seen:
                    self.seen.add(item)
                    return item
                return None

            async def setup(self) -> None:
                self.seen.clear()

            async def cleanup(self) -> None:
                self.seen.clear()

        return self.add_operator(DistinctOperator())

    async def collect(self) -> List[T]:
        """
        Collect all stream items into a list.

        :return: List of all items
        :rtype: List[T]
        """
        return [item async for item in self]

    def take(self, n: int) -> "Stream[T]":
        """
        Take first n items from the stream.

        :param n: Number of items to take
        :type n: int
        :return: New stream with first n items
        :rtype: Stream[T]
        """

        class TakeOperator(Operator[T, T]):
            def __init__(self, n: int):
                self.remaining = n

            async def process(self, item: T) -> Optional[T]:
                if self.remaining > 0:
                    self.remaining -= 1
                    return item
                return None

            async def setup(self) -> None:
                pass

            async def cleanup(self) -> None:
                pass

        return self.add_operator(TakeOperator(n))

    def skip(self, n: int) -> "Stream[T]":
        """
        Skip first n items in the stream.

        :param n: Number of items to skip
        :type n: int
        :return: New stream without first n items
        :rtype: Stream[T]
        """

        class SkipOperator(Operator[T, T]):
            def __init__(self, n: int):
                self.remaining = n

            async def process(self, item: T) -> Optional[T]:
                if self.remaining > 0:
                    self.remaining -= 1
                    return None
                return item

            async def setup(self) -> None:
                pass

            async def cleanup(self) -> None:
                pass

        return self.add_operator(SkipOperator(n))

    async def count(self) -> int:
        """
        Count the number of items in the stream.

        :return: Number of items
        :rtype: int
        """
        count = 0
        async for _ in self:
            count += 1
        return count

    async def first(self) -> Optional[T]:
        """
        Get the first item in the stream.

        :return: First item or None if stream is empty
        :rtype: Optional[T]
        """
        async for item in self:
            return item
        return None

    async def last(self) -> Optional[T]:
        """
        Get the last item in the stream.

        :return: Last item or None if stream is empty
        :rtype: Optional[T]
        """
        last_item = None
        async for item in self:
            last_item = item
        return last_item

    def chain(self, other: Union[AsyncIterable[T], "Stream[T]"]) -> "Stream[T]":
        """
        Chain this stream with another stream.

        :param other: Stream to chain with
        :type other: Union[AsyncIterable[T], Stream[T]]
        :return: New combined stream
        :rtype: Stream[T]
        """

        async def chain_source():
            async for item in self:
                yield item
            if isinstance(other, Stream):
                async for item in other:
                    yield item
            else:
                async for item in other:
                    yield item

        return Stream(chain_source())

    def broadcast(self) -> List["Stream[T]"]:
        """
        Split the stream into multiple identical streams.

        :return: List of identical streams
        :rtype: List[Stream[T]]
        """

        class Broadcaster:
            def __init__(self):
                self.queues: List[asyncio.Queue[Optional[T]]] = []
                self._task: Optional[asyncio.Task] = None

            async def run(self, source: AsyncIterable[T]):
                try:
                    async for item in source:
                        await asyncio.gather(
                            *(queue.put(item) for queue in self.queues)
                        )
                finally:
                    for queue in self.queues:
                        await queue.put(None)

            def add_queue(self) -> asyncio.Queue[Optional[T]]:
                queue: asyncio.Queue[Optional[T]] = asyncio.Queue()
                self.queues.append(queue)
                return queue

            async def start(self, source: AsyncIterable[T]):
                self._task = asyncio.create_task(self.run(source))

            async def stop(self):
                if self._task is not None:
                    self._task.cancel()
                    try:
                        await self._task
                    except asyncio.CancelledError:
                        pass

        broadcaster = Broadcaster()

        async def make_stream() -> AsyncIterator[T]:
            queue = broadcaster.add_queue()
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item

        streams = [Stream(make_stream()) for _ in range(2)]

        # Start broadcasting in the background
        asyncio.create_task(broadcaster.start(self))

        return streams
